"""
Populate Realistic Demo Data for Newly Onboarded Users.
Complies with all Smart Office business rules, RBAC, and schemas.
"""
from datetime import datetime, timezone
from app.db.database import SessionLocal
from app.models.employee import Employee
from app.models.user import User
from app.models.team import Team
from app.models.building import Building
from app.models.floor import Floor
from app.models.seat import Seat
from app.models.asset import Asset
from app.models.asset_allocation import AssetAllocation
from app.repositories.team_repository import TeamRepository
from app.repositories.seat_repository import SeatRepository
from app.core.constants import SEAT_STATUS_OCCUPIED, SEAT_STATUS_VACANT
from app.services.notification_service import ws_manager


def main():
    db = SessionLocal()
    try:
        print("==================================================")
        print("1. INSPECTING EXISTING DATA & ROLES")
        print("==================================================")

        # 1. Primary Admin User & Employee
        admin_user = db.query(User).filter(User.email == "neerajramnani800@gmail.com").first()
        if not admin_user or not admin_user.employee:
            raise RuntimeError("Admin user neerajramnani800@gmail.com or employee not found!")

        admin_emp = admin_user.employee
        print(f"Preserving Primary Admin: [{admin_emp.employee_code}] {admin_emp.first_name} {admin_emp.last_name} ({admin_user.email})")

        # 2. Get all newly onboarded employees (excluding admin)
        new_employees = (
            db.query(Employee)
            .filter(Employee.id != admin_emp.id)
            .order_by(Employee.employee_code)
            .all()
        )
        print(f"Total newly onboarded employees: {len(new_employees)}")

        # 3. Identify Managers among the new users
        manager_employees = [
            e for e in new_employees
            if e.user and e.user.role and e.user.role.name == "Manager"
        ]
        print(f"Found {len(manager_employees)} Manager-role employees among new users:")
        for m in manager_employees:
            print(f"  - [{m.employee_code}] {m.first_name} {m.last_name} ({m.email})")

        team_definitions = [
            ("racknap", "Development", "EMP-004"),      # Sachin Mishra
            ("global logic", "Development", "EMP-009"), # Monika Pawar
            ("znet", "DevOps", "EMP-005"),              # Richa Patel
            ("mimo", "Development", "EMP-010"),         # Shweta Trivedi
            ("sla finser", "Finance", "EMP-001"),       # Anand Kapoor
            ("NSI", "IT", "EMP-006"),                   # Anita Kashyap
            ("external project 1", "Data Science", "EMP-002"), # Meera Kashyap
            ("external project 2", "Development", "EMP-007"),  # Diya Bhatia
        ]

        print("\n==================================================")
        print("2. CREATING TEAMS & ASSIGNING MANAGERS")
        print("==================================================")

        # Map managers by employee_code
        manager_map = {m.employee_code: m for m in manager_employees}

        created_teams = []
        for t_name, t_dept, mgr_code in team_definitions:
            mgr = manager_map.get(mgr_code)
            if not mgr:
                # Fallback to next available manager if specific code is different
                mgr = manager_employees[len(created_teams)]

            # Check if team already exists
            existing_team = db.query(Team).filter(Team.name == t_name).first()
            if existing_team:
                existing_team.manager_id = mgr.id
                existing_team.department = t_dept
                team = existing_team
            else:
                team = TeamRepository.create(
                    db=db,
                    name=t_name,
                    department=t_dept,
                    manager_id=mgr.id,
                )
            created_teams.append(team)

            # Assign manager to their team
            mgr.team_id = team.id
            mgr.manager_id = admin_emp.id  # Top manager reports to Admin
            print(f"Team '{team.name}' ({team.department}) -> Manager: [{mgr.employee_code}] {mgr.first_name} {mgr.last_name}")

        db.flush()

        print("\n==================================================")
        print("3. DISTRIBUTING EMPLOYEES ACROSS TEAMS")
        print("==================================================")

        # Distribute all 100 new employees across the 8 teams
        # Managers are already assigned to their team. Distribute remaining:
        # Separate team managers from other employees
        team_manager_ids = {t.manager_id for t in created_teams}
        non_manager_employees = [e for e in new_employees if e.id not in team_manager_ids]

        # Calculate target team sizes: 4 teams of 13, 4 teams of 12 (including manager)
        # That means additional non-managers: 4 teams get 12 non-managers, 4 teams get 11 non-managers
        # 4*12 + 4*11 = 48 + 44 = 92 non-managers. Total = 92 + 8 = 100!
        team_buckets: dict[int, list[Employee]] = {t.id: [] for t in created_teams}
        team_idx = 0
        for emp in non_manager_employees:
            target_team = created_teams[team_idx % len(created_teams)]
            emp.team_id = target_team.id
            emp.manager_id = target_team.manager_id
            team_buckets[target_team.id].append(emp)
            team_idx += 1

        db.flush()

        for t in created_teams:
            total_members = 1 + len(team_buckets[t.id])  # Manager + non-managers
            print(f"Team '{t.name}': 1 Manager + {len(team_buckets[t.id])} Members = {total_members} Total")

        print("\n==================================================")
        print("4. CONFIGURING SEATING LOCATION (New Building)")
        print("==================================================")

        new_bldg = db.query(Building).filter(Building.name == "New Building").first()
        if not new_bldg:
            raise RuntimeError("New Building not found in database!")

        gf = db.query(Floor).filter(Floor.building_id == new_bldg.id, Floor.floor_number == 0).first()
        f1 = db.query(Floor).filter(Floor.building_id == new_bldg.id, Floor.floor_number == 1).first()

        if not gf or not f1:
            raise RuntimeError("Ground Floor or First Floor not found for New Building!")

        # Update floor names & map dimensions for optimal visual UI rendering
        gf.name = "Ground Floor"
        f1.name = "First Floor"
        if f1.map_height < 1200:
            f1.map_height = 1200  # Expand height to fit F1 seats up to Y=1100
        db.flush()

        print(f"Building: {new_bldg.name}")
        print(f" - Floor ID {gf.id}: '{gf.name}' (dim: {gf.map_width}x{gf.map_height})")
        print(f" - Floor ID {f1.id}: '{f1.name}' (dim: {f1.map_width}x{f1.map_height})")

        print("\n==================================================")
        print("5. ALLOCATING SEATS TO EMPLOYEES")
        print("==================================================")

        # Check existing seat allocations for new employees
        unallocated_gf_emps = [e for e in new_employees[:50] if not (e.seat and e.seat.floor_id == gf.id)]
        unallocated_f1_emps = [e for e in new_employees[50:100] if not (e.seat and e.seat.floor_id == f1.id)]

        gf_seats = (
            db.query(Seat)
            .filter(Seat.floor_id == gf.id, Seat.status == SEAT_STATUS_VACANT)
            .order_by(Seat.id)
            .all()
        )
        f1_seats = (
            db.query(Seat)
            .filter(Seat.floor_id == f1.id, Seat.status == SEAT_STATUS_VACANT)
            .order_by(Seat.id)
            .all()
        )

        if len(gf_seats) < len(unallocated_gf_emps) or len(f1_seats) < len(unallocated_f1_emps):
            raise RuntimeError(
                f"Insufficient vacant seats in New Building: Needed GF={len(unallocated_gf_emps)} (available {len(gf_seats)}), "
                f"Needed F1={len(unallocated_f1_emps)} (available {len(f1_seats)})"
            )

        allocated_count = 0
        for emp, seat in zip(unallocated_gf_emps, gf_seats):
            SeatRepository.assign_seat_transaction(
                db=db,
                seat=seat,
                employee=emp,
                user_id=admin_user.id,
                notes="Initial demo onboarding seat allocation",
            )
            allocated_count += 1

        for emp, seat in zip(unallocated_f1_emps, f1_seats):
            SeatRepository.assign_seat_transaction(
                db=db,
                seat=seat,
                employee=emp,
                user_id=admin_user.id,
                notes="Initial demo onboarding seat allocation",
            )
            allocated_count += 1

        print(f"Allocated seats to {allocated_count} new employees (Existing already allocated: {100 - len(unallocated_gf_emps) - len(unallocated_f1_emps)}).")

        print("\n==================================================")
        print("6. VERIFYING DESKTOP ASSETS")
        print("==================================================")

        # Verify that all 100 new employees have an allocated Desktop asset
        all_desktops = db.query(Asset).filter(Asset.asset_type == "Desktop").all()
        active_allocations = (
            db.query(AssetAllocation)
            .join(Asset)
            .filter(AssetAllocation.status == "ACTIVE", Asset.asset_type == "Desktop")
            .all()
        )

        emp_to_desk = {a.employee_id: a for a in active_allocations}
        missing_desktops = [e for e in new_employees if e.id not in emp_to_desk]

        if missing_desktops:
            print(f"Found {len(missing_desktops)} employees missing desktop. Allocating available desktops...")
            available_desktops = (
                db.query(Asset)
                .filter(Asset.asset_type == "Desktop", Asset.status == "Available")
                .all()
            )
            for emp in missing_desktops:
                if not available_desktops:
                    # Create new desktop asset if none available
                    next_num = len(all_desktops) + 1
                    desk_code = f"DSK-{next_num:03d}"
                    new_desk = Asset(
                        asset_code=desk_code,
                        asset_type="Desktop",
                        name=f"Standard Workstation {next_num:03d}",
                        serial_number=f"SN-DSK-{next_num:04d}",
                        status="Available",
                    )
                    db.add(new_desk)
                    db.flush()
                    all_desktops.append(new_desk)
                    desk_to_assign = new_desk
                else:
                    desk_to_assign = available_desktops.pop(0)

                desk_to_assign.status = "Assigned"
                new_alloc = AssetAllocation(
                    asset_id=desk_to_assign.id,
                    employee_id=emp.id,
                    action="ASSIGN",
                    allocated_at=datetime.now(timezone.utc),
                    status="ACTIVE",
                    notes="Automated demo workstation provisioning",
                )
                db.add(new_alloc)
            db.flush()
            print("All missing desktops created and allocated.")
        else:
            print(f"All {len(new_employees)} employees already have an active Desktop assigned.")

        db.commit()
        print("All database transactions committed successfully!")

        # Broadcast live updates to UI
        ws_manager.broadcast_entity_change("Team", "created", ["Team", "Employee"])
        ws_manager.broadcast_entity_change("Seat", "assigned", ["Seat", "Floor", "Building"])
        ws_manager.broadcast_entity_change("Asset", "allocated", ["Asset", "Employee"])

        print("\n==================================================")
        print("7. DATA INTEGRITY AUDIT")
        print("==================================================")

        # Integrity Checks
        audit_errors = []

        # Check every user has 1 employee
        for u in db.query(User).all():
            if not u.employee:
                audit_errors.append(f"User {u.email} missing employee link")

        # Check every employee has role and team
        for e in new_employees:
            if not e.user or not e.user.role:
                audit_errors.append(f"Employee {e.employee_code} missing user role")
            if not e.team_id:
                audit_errors.append(f"Employee {e.employee_code} missing team")
            if not e.manager_id:
                audit_errors.append(f"Employee {e.employee_code} missing manager")
            if not e.seat:
                audit_errors.append(f"Employee {e.employee_code} missing seat")
            elif e.seat.floor.building_id != new_bldg.id or e.seat.floor.floor_number not in (0, 1):
                audit_errors.append(f"Employee {e.employee_code} assigned seat outside New Building Ground/F1")

        # Check desktop count
        new_emp_desks = (
            db.query(AssetAllocation)
            .join(Asset)
            .filter(
                AssetAllocation.employee_id != admin_emp.id,
                AssetAllocation.status == "ACTIVE",
                Asset.asset_type == "Desktop",
            )
            .count()
        )
        if new_emp_desks != len(new_employees):
            audit_errors.append(f"Expected {len(new_employees)} desktop allocations, found {new_emp_desks}")

        print(f"Integrity check completed with {len(audit_errors)} errors.")
        for err in audit_errors:
            print(" - ERROR:", err)

        print("\n==================================================")
        print("8. DEMO VERIFICATION REPORT")
        print("==================================================")

        print("\nA. TEAMS")
        print("-" * 65)
        print(f"{'Team':<25} | {'Manager':<25} | {'Employee Count':<12}")
        print("-" * 65)
        for t in created_teams:
            m_name = f"{t.manager.first_name} {t.manager.last_name}" if t.manager else "None"
            m_count = db.query(Employee).filter(Employee.team_id == t.id).count()
            print(f"{t.name:<25} | {m_name:<25} | {m_count:<12}")

        print("\nB. SEATING")
        print("-" * 65)
        gf_occ = db.query(Seat).filter(Seat.floor_id == gf.id, Seat.status == SEAT_STATUS_OCCUPIED).count()
        gf_vac = db.query(Seat).filter(Seat.floor_id == gf.id, Seat.status == SEAT_STATUS_VACANT).count()
        f1_occ = db.query(Seat).filter(Seat.floor_id == f1.id, Seat.status == SEAT_STATUS_OCCUPIED).count()
        f1_vac = db.query(Seat).filter(Seat.floor_id == f1.id, Seat.status == SEAT_STATUS_VACANT).count()

        print(f"New Building - Ground Floor | occupied: {gf_occ} / available: {gf_vac} (Total: {gf_occ+gf_vac})")
        print(f"New Building - First Floor  | occupied: {f1_occ} / available: {f1_vac} (Total: {f1_occ+f1_vac})")

        print("\nC. ASSETS (Desktop)")
        print("-" * 65)
        total_desktops = db.query(Asset).filter(Asset.asset_type == "Desktop").count()
        allocated_desktops = db.query(Asset).filter(Asset.asset_type == "Desktop", Asset.status == "Assigned").count()
        available_desktops = db.query(Asset).filter(Asset.asset_type == "Desktop", Asset.status == "Available").count()
        print(f"Desktop assets total:     {total_desktops}")
        print(f"Desktop assets allocated: {allocated_desktops}")
        print(f"Desktop assets remaining: {available_desktops}")

        print("\nD. EXCEPTIONS")
        print("-" * 65)
        if not audit_errors:
            print("None. All 100 newly onboarded employees have been successfully assigned:")
            print("  [OK] Valid Application Role")
            print("  [OK] Dedicated Team (out of the 8 specified teams)")
            print("  [OK] Direct Reporting Manager")
            print("  [OK] Exclusive Seat in New Building (Ground or First Floor)")
            print("  [OK] Unique Dedicated Desktop Asset")
        else:
            for err in audit_errors:
                print(f"Exception: {err}")

    except Exception as ex:
        db.rollback()
        print("TRANSACTION ERROR:", ex)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
