from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .routes import auth, invoices, upload, columns, export, categories, admin, project, filetools, org, audit, pm, construction_health, compliance, lender_plus, lender_risk, permits, safety, labour, bid, ai_risk, co_approval, selections, equipment, notifications, lien_release, spec_review, prequalification, client_hub, syndicate, erp_integration, cfo_reports, subcontract, canadian_legal, quality


def _run_migrations():
    """Add any missing columns to existing tables (safe to run on every start)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE category_configs ADD COLUMN requires_sub_division BOOLEAN DEFAULT 0",
            "ALTER TABLE column_configs ADD COLUMN is_exportable BOOLEAN DEFAULT 1",
            "ALTER TABLE column_configs ADD COLUMN is_viewable BOOLEAN DEFAULT 1",
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN payment_status VARCHAR DEFAULT 'unpaid'",
            "ALTER TABLE invoices ADD COLUMN amount_paid FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN billed_to VARCHAR",
            "ALTER TABLE invoices ADD COLUMN billing_type VARCHAR",
            "ALTER TABLE invoices ADD COLUMN vendor_on_record VARCHAR",
            "ALTER TABLE invoices ADD COLUMN draw_id INTEGER REFERENCES draws(id)",
            "ALTER TABLE invoices ADD COLUMN claim_id INTEGER REFERENCES claims(id)",
            # Dual claim FKs
            "ALTER TABLE invoices ADD COLUMN provincial_claim_id INTEGER REFERENCES claims(id)",
            "ALTER TABLE invoices ADD COLUMN federal_claim_id INTEGER REFERENCES claims(id)",
            # Tax breakdown
            "ALTER TABLE invoices ADD COLUMN subtotal FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_gst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_hst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_qst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_pst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_total FLOAT",
            "ALTER TABLE invoices ADD COLUMN vendor_province VARCHAR",
            # Cost tracking
            "ALTER TABLE invoices ADD COLUMN received_total FLOAT",
            "ALTER TABLE invoices ADD COLUMN lender_margin_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN lender_margin_amt FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN lender_submitted_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN lender_approved_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN lender_status VARCHAR DEFAULT 'pending'",
            "ALTER TABLE invoices ADD COLUMN lender_tax_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN govt_margin_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN govt_margin_amt FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN govt_submitted_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN govt_approved_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN govt_status VARCHAR DEFAULT 'pending'",
            "ALTER TABLE invoices ADD COLUMN is_payroll BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_demo BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN project_id INTEGER REFERENCES projects(id)",
            "ALTER TABLE projects ADD COLUMN lender_budget REAL",
            "ALTER TABLE cost_categories ADD COLUMN lender_budget REAL",
            "ALTER TABLE invoices ADD COLUMN holdback_pct REAL DEFAULT 10.0",
            "ALTER TABLE invoices ADD COLUMN holdback_released BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN holdback_released_date TEXT",
            "ALTER TABLE invoices ADD COLUMN approval_status TEXT DEFAULT 'pending'",
            "ALTER TABLE invoices ADD COLUMN approved_by TEXT",
            "ALTER TABLE invoices ADD COLUMN approved_at TEXT",
            """CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                actual_date TEXT,
                pct_complete REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS lien_waivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                subcontractor_id INTEGER REFERENCES subcontractors(id),
                vendor_name TEXT,
                waiver_type TEXT NOT NULL,
                amount REAL,
                date_received TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS project_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                doc_type TEXT NOT NULL DEFAULT 'other',
                title TEXT NOT NULL,
                file_path TEXT,
                original_filename TEXT,
                external_url TEXT,
                notes TEXT,
                draw_id INTEGER REFERENCES draws(id),
                category_id INTEGER REFERENCES cost_categories(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS lender_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                token TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                created_by INTEGER NOT NULL REFERENCES users(id),
                is_active INTEGER DEFAULT 1,
                expires_at TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS subcontractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                trade TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                contract_value REAL,
                status TEXT DEFAULT 'active',
                insurance_expiry TEXT,
                wsib_expiry TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS committed_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category_id INTEGER REFERENCES cost_categories(id),
                vendor TEXT NOT NULL,
                description TEXT,
                contract_amount REAL NOT NULL,
                invoiced_to_date REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                contract_date TEXT,
                expected_completion TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS change_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category_id INTEGER REFERENCES cost_categories(id),
                co_number TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                issued_by TEXT,
                date TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Multi-tenant: organisations
            """CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                plan TEXT DEFAULT 'starter',
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS organization_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                role TEXT DEFAULT 'editor',
                is_active INTEGER DEFAULT 1,
                invited_by INTEGER REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS org_vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                vendor_code TEXT,
                name TEXT NOT NULL,
                trade TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                address TEXT,
                payment_terms TEXT,
                hst_number TEXT,
                wsib_number TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "ALTER TABLE projects ADD COLUMN org_id INTEGER REFERENCES organizations(id)",
            "ALTER TABLE invoices ADD COLUMN org_id INTEGER REFERENCES organizations(id)",
            "CREATE INDEX IF NOT EXISTS ix_projects_org_id ON projects(org_id)",
            "CREATE INDEX IF NOT EXISTS ix_invoices_org_id ON invoices(org_id)",
            "CREATE INDEX IF NOT EXISTS ix_org_members_org_user ON organization_members(org_id, user_id)",
            """CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token TEXT UNIQUE NOT NULL,
                expires_at DATETIME NOT NULL,
                used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS org_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                email TEXT NOT NULL,
                role TEXT DEFAULT 'editor',
                token TEXT UNIQUE NOT NULL,
                invited_by INTEGER NOT NULL REFERENCES users(id),
                expires_at DATETIME NOT NULL,
                accepted_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                user_id INTEGER REFERENCES users(id),
                username TEXT,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id INTEGER,
                detail TEXT,
                ip_address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_org_created ON audit_logs(org_id, created_at)",
            # PM tables
            """CREATE TABLE IF NOT EXISTS pm_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                parent_id INTEGER REFERENCES pm_tasks(id),
                title TEXT NOT NULL,
                description TEXT,
                task_type TEXT DEFAULT 'task',
                status TEXT DEFAULT 'not_started',
                priority TEXT DEFAULT 'medium',
                assigned_to INTEGER REFERENCES users(id),
                start_date TEXT, end_date TEXT, due_date TEXT,
                percent_complete INTEGER DEFAULT 0,
                location TEXT, tags TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_task_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES pm_tasks(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                comment TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_daily_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                log_date TEXT NOT NULL,
                weather TEXT, temperature TEXT, crew_count INTEGER DEFAULT 0,
                work_summary TEXT, issues TEXT, delays TEXT, visitors TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_rfis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                rfi_number TEXT NOT NULL,
                subject TEXT NOT NULL, description TEXT,
                status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium',
                assigned_to INTEGER REFERENCES users(id),
                due_date TEXT, response TEXT,
                responded_by INTEGER REFERENCES users(id),
                responded_at DATETIME,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_punch_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                item_number TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT, location TEXT,
                status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium',
                assigned_to INTEGER REFERENCES users(id),
                due_date TEXT, resolved_at DATETIME, photo_path TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_submittals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                submittal_number TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT, spec_section TEXT,
                status TEXT DEFAULT 'draft',
                submitted_by INTEGER REFERENCES users(id),
                submitted_date TEXT,
                reviewer INTEGER REFERENCES users(id),
                review_date TEXT, review_notes TEXT, file_path TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                meeting_date TEXT NOT NULL, title TEXT NOT NULL,
                location TEXT, attendees TEXT, agenda TEXT,
                minutes TEXT, action_items TEXT, next_meeting TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS pm_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                file_path TEXT NOT NULL, original_filename TEXT,
                caption TEXT, location TEXT,
                category TEXT DEFAULT 'general',
                taken_date TEXT,
                task_id INTEGER REFERENCES pm_tasks(id),
                punch_item_id INTEGER REFERENCES pm_punch_items(id),
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_pm_tasks_project ON pm_tasks(project_id, org_id)",
            "CREATE INDEX IF NOT EXISTS ix_pm_tasks_assigned ON pm_tasks(assigned_to)",
            # Lender+ tables
            """CREATE TABLE IF NOT EXISTS funding_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                description TEXT NOT NULL,
                condition_type TEXT DEFAULT 'document',
                status TEXT DEFAULT 'open',
                required_by TEXT, satisfied_date TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS draw_certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                cert_type TEXT DEFAULT 'progress',
                certifier_name TEXT, certifier_firm TEXT,
                cert_date TEXT, amount_certified REAL,
                file_path TEXT, original_filename TEXT,
                status TEXT DEFAULT 'pending', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS statutory_declarations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                vendor_name TEXT NOT NULL,
                vendor_id INTEGER REFERENCES org_vendors(id),
                declaration_date TEXT, period_end TEXT,
                amount REAL, file_path TEXT,
                status TEXT DEFAULT 'required',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS owner_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                token TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                created_by INTEGER NOT NULL REFERENCES users(id),
                is_active INTEGER DEFAULT 1,
                expires_at TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_funding_conditions_draw ON funding_conditions(draw_id)",
            "CREATE INDEX IF NOT EXISTS ix_draw_certs_draw ON draw_certificates(draw_id)",
            "CREATE INDEX IF NOT EXISTS ix_stat_decls_draw ON statutory_declarations(draw_id)",
            # Canadian Compliance
            """CREATE TABLE IF NOT EXISTS prompt_payment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                invoice_id INTEGER REFERENCES invoices(id),
                payment_type TEXT NOT NULL,
                proper_invoice_date TEXT, certifier_cert_date TEXT,
                payment_deadline TEXT, paid_date TEXT,
                is_overdue INTEGER DEFAULT 0,
                province TEXT DEFAULT 'ON',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Compliance fields on org_vendors (safe ALTER IF NOT EXISTS)
            "ALTER TABLE org_vendors ADD COLUMN wsib_expiry TEXT",
            "ALTER TABLE org_vendors ADD COLUMN wcb_number TEXT",
            "ALTER TABLE org_vendors ADD COLUMN wcb_expiry TEXT",
            "ALTER TABLE org_vendors ADD COLUMN insurance_expiry TEXT",
            "ALTER TABLE org_vendors ADD COLUMN liability_limit REAL",
            "ALTER TABLE org_vendors ADD COLUMN cra_business_number TEXT",
            "ALTER TABLE org_vendors ADD COLUMN province TEXT DEFAULT 'ON'",
            "ALTER TABLE org_vendors ADD COLUMN is_incorporated INTEGER DEFAULT 0",
            "ALTER TABLE org_vendors ADD COLUMN statutory_declaration_date TEXT",
            # Province + contingency on projects
            "ALTER TABLE projects ADD COLUMN province TEXT DEFAULT 'ON'",
            "ALTER TABLE projects ADD COLUMN contingency_budget REAL",
            # AI suggestions log (optional — stores Gemini suggestions for audit)
            """CREATE TABLE IF NOT EXISTS ai_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                project_id INTEGER REFERENCES projects(id),
                invoice_id INTEGER REFERENCES invoices(id),
                suggested_category_id INTEGER REFERENCES cost_categories(id),
                suggested_sub_category_id INTEGER REFERENCES cost_sub_categories(id),
                confidence REAL,
                reasoning TEXT,
                accepted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Lender Risk: Covenants + Interest Reserve
            """CREATE TABLE IF NOT EXISTS lender_covenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                covenant_type TEXT NOT NULL,
                name TEXT NOT NULL,
                threshold_value REAL,
                threshold_operator TEXT DEFAULT '<=',
                current_value REAL,
                as_of_date TEXT,
                status TEXT DEFAULT 'compliant',
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS interest_reserves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                reserve_amount REAL NOT NULL,
                drawn_to_date REAL DEFAULT 0,
                interest_rate REAL,
                accrual_basis TEXT DEFAULT 'actual/365',
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS interest_reserve_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reserve_id INTEGER NOT NULL REFERENCES interest_reserves(id),
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_date TEXT NOT NULL,
                amount REAL NOT NULL,
                period_start TEXT, period_end TEXT, notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Bond Registry
            """CREATE TABLE IF NOT EXISTS bonds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                vendor_id INTEGER REFERENCES org_vendors(id),
                vendor_name TEXT,
                bond_type TEXT NOT NULL,
                bond_number TEXT,
                surety_company TEXT,
                bond_amount REAL,
                effective_date TEXT,
                expiry_date TEXT,
                status TEXT DEFAULT 'active',
                file_path TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Permit & Inspection Workflow
            """CREATE TABLE IF NOT EXISTS permits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                permit_type TEXT NOT NULL,
                permit_number TEXT,
                description TEXT NOT NULL,
                authority TEXT,
                application_date TEXT, issued_date TEXT, expiry_date TEXT,
                status TEXT DEFAULT 'pending',
                fee_paid REAL, file_path TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS permit_inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                permit_id INTEGER NOT NULL REFERENCES permits(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                inspection_type TEXT NOT NULL,
                scheduled_date TEXT, completed_date TEXT,
                inspector_name TEXT,
                result TEXT DEFAULT 'pending',
                deficiencies TEXT, notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Safety Management
            """CREATE TABLE IF NOT EXISTS safety_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                incident_date TEXT NOT NULL,
                incident_type TEXT NOT NULL,
                severity TEXT DEFAULT 'low',
                description TEXT NOT NULL,
                location TEXT,
                persons_involved TEXT,
                immediate_actions TEXT,
                root_cause TEXT,
                corrective_actions TEXT,
                wsib_reportable INTEGER DEFAULT 0,
                wsib_reported_date TEXT,
                mol_reportable INTEGER DEFAULT 0,
                mol_reported_date TEXT,
                status TEXT DEFAULT 'open',
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS toolbox_talks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                talk_date TEXT NOT NULL,
                topic TEXT NOT NULL,
                facilitator TEXT,
                attendee_count INTEGER DEFAULT 0,
                attendees TEXT,
                duration_minutes INTEGER,
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Warranty Items
            """CREATE TABLE IF NOT EXISTS warranty_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                item_number TEXT,
                category TEXT DEFAULT 'other',
                description TEXT NOT NULL,
                location TEXT,
                reported_date TEXT,
                warranty_type TEXT DEFAULT '1year',
                homeowner_name TEXT,
                status TEXT DEFAULT 'open',
                assigned_to TEXT,
                scheduled_date TEXT,
                resolved_date TEXT,
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Labour Time Tracking
            """CREATE TABLE IF NOT EXISTS timecards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                worker_name TEXT NOT NULL,
                trade TEXT,
                classification TEXT,
                work_date TEXT NOT NULL,
                regular_hours REAL DEFAULT 0,
                overtime_hours REAL DEFAULT 0,
                double_time_hours REAL DEFAULT 0,
                hourly_rate REAL,
                burden_pct REAL DEFAULT 0,
                cost_category_id INTEGER REFERENCES cost_categories(id),
                work_description TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_timecards_project_date ON timecards(project_id, work_date)",
            "CREATE INDEX IF NOT EXISTS ix_safety_incidents_project ON safety_incidents(project_id)",
            "CREATE INDEX IF NOT EXISTS ix_permits_project ON permits(project_id)",
            "CREATE INDEX IF NOT EXISTS ix_lender_covenants_project ON lender_covenants(project_id)",
            # Bid Management
            """CREATE TABLE IF NOT EXISTS bid_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                package_number TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                trade_category TEXT,
                issue_date TEXT, due_date TEXT,
                estimated_value REAL,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS bid_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id INTEGER NOT NULL REFERENCES bid_packages(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                vendor_id INTEGER REFERENCES org_vendors(id),
                vendor_name TEXT NOT NULL,
                contact_email TEXT,
                submitted_date TEXT,
                total_amount REAL,
                inclusions TEXT, exclusions TEXT, qualifications TEXT,
                status TEXT DEFAULT 'invited',
                invite_token TEXT UNIQUE,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_bid_packages_project ON bid_packages(project_id)",
            "CREATE INDEX IF NOT EXISTS ix_bid_responses_token ON bid_responses(invite_token)",
            # CO Approval Tokens
            """CREATE TABLE IF NOT EXISTS co_approval_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                co_id INTEGER NOT NULL REFERENCES change_orders(id),
                token TEXT UNIQUE NOT NULL,
                client_name TEXT,
                client_email TEXT,
                approved_at DATETIME,
                rejected_at DATETIME,
                rejection_reason TEXT,
                expires_at DATETIME,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_co_approval_token ON co_approval_tokens(token)",
            # Client Selections
            """CREATE TABLE IF NOT EXISTS client_selection_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS client_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category_id INTEGER REFERENCES client_selection_categories(id) ON DELETE SET NULL,
                item_name TEXT NOT NULL,
                description TEXT,
                standard_option TEXT, client_choice TEXT,
                allowance_amount REAL, actual_cost REAL, upgrade_amount REAL,
                status TEXT DEFAULT 'pending',
                due_date TEXT, notes TEXT,
                client_approved_at DATETIME,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS client_selection_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                token TEXT UNIQUE NOT NULL,
                client_name TEXT, client_email TEXT,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Equipment
            """CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                equipment_code TEXT,
                name TEXT NOT NULL,
                equipment_type TEXT, make TEXT, model TEXT, year INTEGER,
                serial_number TEXT,
                ownership TEXT DEFAULT 'owned',
                daily_rate REAL, hourly_rate REAL,
                status TEXT DEFAULT 'available',
                current_project_id INTEGER REFERENCES projects(id),
                operator_name TEXT,
                next_service_date TEXT, insurance_expiry TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS equipment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER REFERENCES projects(id),
                log_date TEXT NOT NULL,
                log_type TEXT DEFAULT 'usage',
                hours_used REAL DEFAULT 0,
                fuel_litres REAL, operator_name TEXT,
                work_description TEXT, cost REAL, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_equipment_org ON equipment(org_id)",
            "CREATE INDEX IF NOT EXISTS ix_equipment_logs_eq ON equipment_logs(equipment_id, log_date)",
            # Lien Releases
            """CREATE TABLE IF NOT EXISTS lien_releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                release_type TEXT NOT NULL,
                vendor_id INTEGER REFERENCES org_vendors(id),
                vendor_name TEXT,
                holdback_amount REAL,
                lien_expiry_date TEXT, release_date TEXT, payment_date TEXT,
                status TEXT DEFAULT 'pending',
                statutory_declaration_received INTEGER DEFAULT 0,
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_lien_releases_project ON lien_releases(project_id)",
            # AI Spec Review
            """CREATE TABLE IF NOT EXISTS spec_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                filename TEXT, status TEXT DEFAULT 'pending',
                findings JSON, summary TEXT, total_issues INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Drawing Register
            """CREATE TABLE IF NOT EXISTS drawing_register (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                drawing_number TEXT NOT NULL, title TEXT NOT NULL,
                discipline TEXT, current_revision TEXT, revision_date TEXT,
                status TEXT DEFAULT 'issued', file_path TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_drawings_project ON drawing_register(project_id, discipline)",
            # Subcontractor Prequalification
            """CREATE TABLE IF NOT EXISTS sub_prequalifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                vendor_id INTEGER REFERENCES org_vendors(id),
                company_name TEXT NOT NULL, trade TEXT,
                contact_name TEXT, contact_email TEXT,
                years_in_business INTEGER, annual_revenue REAL,
                bonding_capacity REAL, largest_project REAL,
                safety_record TEXT, wsib_number TEXT, cra_bn TEXT, hst_number TEXT,
                references TEXT, status TEXT DEFAULT 'submitted',
                notes TEXT, invite_token TEXT UNIQUE,
                submitted_at DATETIME, reviewed_by INTEGER REFERENCES users(id), reviewed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_prequal_token ON sub_prequalifications(invite_token)",
            "CREATE INDEX IF NOT EXISTS ix_prequal_org ON sub_prequalifications(org_id)",
            # Client Hub
            """CREATE TABLE IF NOT EXISTS client_hub_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                title TEXT NOT NULL, body TEXT, milestone TEXT,
                photo_paths JSON, visibility TEXT DEFAULT 'client',
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS client_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                sender_type TEXT NOT NULL, sender_name TEXT,
                message TEXT NOT NULL, is_read INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Union Compliance
            """CREATE TABLE IF NOT EXISTS union_agreements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                trade TEXT NOT NULL, local_number TEXT,
                agreement_type TEXT DEFAULT 'iba',
                apprentice_ratio TEXT,
                journeymen_count INTEGER DEFAULT 0, apprentice_count INTEGER DEFAULT 0,
                expiry_date TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Project Closeout
            """CREATE TABLE IF NOT EXISTS closeout_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category TEXT NOT NULL, item_name TEXT NOT NULL,
                description TEXT, responsible_party TEXT, due_date TEXT,
                status TEXT DEFAULT 'pending', completed_at DATETIME, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_closeout_project ON closeout_items(project_id)",
            # Syndicated Loans
            """CREATE TABLE IF NOT EXISTS loan_syndicates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                facility_name TEXT NOT NULL,
                total_commitment REAL NOT NULL,
                currency TEXT DEFAULT 'CAD',
                lead_lender TEXT,
                closing_date TEXT, maturity_date TEXT,
                interest_rate REAL, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS syndicate_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                syndicate_id INTEGER NOT NULL REFERENCES loan_syndicates(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                lender_name TEXT NOT NULL,
                participation_pct REAL NOT NULL,
                commitment_amount REAL,
                contact_name TEXT, contact_email TEXT, reporting_email TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_loan_syndicates_project ON loan_syndicates(project_id)",
            # ERP Credentials
            """CREATE TABLE IF NOT EXISTS erp_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                erp_type TEXT NOT NULL,
                label TEXT NOT NULL,
                endpoint_url TEXT,
                credentials JSON,
                is_active INTEGER DEFAULT 0,
                last_sync DATETIME,
                last_sync_status TEXT,
                sync_log TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_erp_credentials_org ON erp_credentials(org_id)",
            # Subcontract Agreements
            """CREATE TABLE IF NOT EXISTS subcontract_agreements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                bid_response_id INTEGER REFERENCES bid_responses(id),
                vendor_id INTEGER REFERENCES org_vendors(id),
                vendor_name TEXT NOT NULL, trade TEXT, contract_number TEXT,
                scope_of_work TEXT, inclusions TEXT, exclusions TEXT,
                contract_amount REAL NOT NULL, holdback_pct REAL DEFAULT 10,
                payment_terms TEXT, start_date TEXT, end_date TEXT,
                insurance_required INTEGER DEFAULT 1, bond_required INTEGER DEFAULT 0,
                warranty_period TEXT, dispute_resolution TEXT DEFAULT 'CCDC',
                governing_law TEXT, status TEXT DEFAULT 'draft',
                sign_token TEXT UNIQUE, signed_at DATETIME,
                signed_by_name TEXT, signed_by_ip TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_subcontracts_project ON subcontract_agreements(project_id)",
            "CREATE INDEX IF NOT EXISTS ix_subcontracts_token ON subcontract_agreements(sign_token)",
            # Canadian Legal
            """CREATE TABLE IF NOT EXISTS non_payment_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                invoice_id INTEGER REFERENCES invoices(id),
                payment_type TEXT NOT NULL,
                proper_invoice_date TEXT, certifier_cert_date TEXT,
                payment_deadline TEXT, notice_date TEXT,
                disputed_amount REAL, non_disputed_amount REAL,
                reasons TEXT, vendor_name TEXT, vendor_address TEXT,
                province TEXT DEFAULT 'ON', status TEXT DEFAULT 'draft',
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS substantial_performance_certs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                contract_amount REAL, certified_amount REAL, holdback_amount REAL,
                certification_date TEXT, publication_date TEXT,
                lien_expiry_date TEXT, holdback_release_date TEXT,
                consultant_name TEXT, consultant_firm TEXT,
                owner_name TEXT, contractor_name TEXT,
                province TEXT DEFAULT 'ON', status TEXT DEFAULT 'draft',
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Sources & Uses
            """CREATE TABLE IF NOT EXISTS sources_uses_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                entry_type TEXT NOT NULL, category TEXT NOT NULL,
                description TEXT NOT NULL,
                budgeted_amount REAL DEFAULT 0, actual_amount REAL,
                variance REAL, as_of_date TEXT, notes TEXT,
                display_order INTEGER DEFAULT 100,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_sources_uses_project ON sources_uses_entries(project_id)",
            # Estimating
            """CREATE TABLE IF NOT EXISTS estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL, description TEXT,
                status TEXT DEFAULT 'draft', version INTEGER DEFAULT 1, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS estimate_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimate_id INTEGER NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                division TEXT, description TEXT NOT NULL,
                quantity REAL, unit TEXT, unit_cost REAL, total_cost REAL,
                cost_category_id INTEGER REFERENCES cost_categories(id),
                labour_pct REAL, material_pct REAL,
                subcontracted INTEGER DEFAULT 0,
                notes TEXT, display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_estimates_project ON estimates(project_id)",
            # Quality Inspections
            """CREATE TABLE IF NOT EXISTS quality_inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                inspection_date TEXT NOT NULL,
                inspector_name TEXT, area_location TEXT,
                inspection_type TEXT NOT NULL,
                status TEXT DEFAULT 'scheduled',
                pass_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0,
                notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS quality_inspection_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_id INTEGER NOT NULL REFERENCES quality_inspections(id) ON DELETE CASCADE,
                item_description TEXT NOT NULL,
                result TEXT DEFAULT 'pending',
                notes TEXT, display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_quality_inspections_project ON quality_inspections(project_id)",
            # Visitor Log
            """CREATE TABLE IF NOT EXISTS visitor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                visit_date TEXT NOT NULL, visitor_name TEXT NOT NULL,
                visitor_company TEXT, visitor_type TEXT DEFAULT 'other',
                purpose TEXT, host_name TEXT,
                time_in TEXT, time_out TEXT, badge_number TEXT,
                safety_orientation INTEGER DEFAULT 0, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_visitor_logs_project ON visitor_logs(project_id, visit_date)",
            # Vendor Scores
            """CREATE TABLE IF NOT EXISTS vendor_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                vendor_id INTEGER REFERENCES org_vendors(id),
                vendor_name TEXT NOT NULL,
                period TEXT,
                quality INTEGER, timeliness INTEGER,
                safety_score INTEGER, communication INTEGER, value INTEGER,
                would_rehire INTEGER,
                comments TEXT,
                rated_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists or table exists


def _retire_default_admin():
    """Block login with the old default password 'admin123' by rehashing to a random value."""
    from passlib.context import CryptContext
    from .database import SessionLocal
    from .models import User
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin and pwd.verify("admin123", admin.hashed_password):
            new_pw = os.getenv("ADMIN_PASSWORD", "")
            if new_pw and new_pw != "admin123" and len(new_pw) >= 8:
                admin.hashed_password = pwd.hash(new_pw)
                db.commit()
                print("INFO: Admin password updated from .env ADMIN_PASSWORD.")
            else:
                import secrets
                admin.hashed_password = pwd.hash(secrets.token_urlsafe(32))
                db.commit()
                print("WARNING: Admin 'admin123' password retired. Set ADMIN_PASSWORD in .env and re-run create_admin.py.")
    finally:
        db.close()


def _seed_existing_user_orgs():
    """On startup: ensure every existing user has an org (migration for pre-org users)."""
    from .database import SessionLocal
    from .models import User as _User
    from .seed_org import ensure_user_org
    db = SessionLocal()
    try:
        users = db.query(_User).filter(_User.is_active == True).all()
        for user in users:
            try:
                ensure_user_org(db, user)
            except Exception:
                db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _retire_default_admin()
    _seed_existing_user_orgs()
    _upload_dir = os.getenv("UPLOAD_FOLDER", "./uploads")
    os.makedirs(_upload_dir, mode=0o700, exist_ok=True)
    os.makedirs(os.path.join(_upload_dir, "docs"), mode=0o700, exist_ok=True)
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' 'unsafe-inline' "
            "https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
            "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "object-src blob:; "
            "frame-src blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response


_disable_docs = os.getenv("DISABLE_DOCS", "true").lower() in ("1", "true", "yes")

app = FastAPI(
    title="Finel AI Invoice Extractor",
    description="AI-powered invoice extraction using Google Gemini",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Organization-Id"],
)


# API routes
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(upload.router)
app.include_router(columns.router)
app.include_router(categories.router)
app.include_router(export.router)
app.include_router(admin.router)
app.include_router(project.router)
app.include_router(project._lender_router)
app.include_router(filetools.router)
app.include_router(org.router)
app.include_router(audit.router)
app.include_router(pm.router)
app.include_router(construction_health.router)
app.include_router(compliance.router)
app.include_router(lender_plus.router)
app.include_router(lender_plus._owner_router)
app.include_router(lender_risk.router)
app.include_router(permits.router)
app.include_router(safety.router)
app.include_router(labour.router)
app.include_router(bid.router)
app.include_router(bid._bid_portal_router)
app.include_router(ai_risk.router)
app.include_router(ai_risk._portfolio_router)
app.include_router(co_approval.router)
app.include_router(co_approval._public_router)
app.include_router(selections.router)
app.include_router(selections._public_router)
app.include_router(equipment.router)
app.include_router(notifications.router)
app.include_router(lien_release.router)
app.include_router(spec_review.router)
app.include_router(prequalification.router)
app.include_router(prequalification._public_router)
app.include_router(client_hub.router)
app.include_router(client_hub._weather_router)
app.include_router(client_hub._union_router)
app.include_router(client_hub._closeout_router)
app.include_router(syndicate.router)
app.include_router(erp_integration.router)
app.include_router(cfo_reports.router)
app.include_router(subcontract.router)
app.include_router(subcontract._public_router)
app.include_router(canadian_legal.router)
app.include_router(quality.router)

# Serve static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    """Serve the PWA service worker from root scope so it can control the whole app."""
    from fastapi.responses import FileResponse
    sw_path = os.path.join(static_dir, "sw.js")
    return FileResponse(sw_path, media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})


@app.get("/lender/{token}", include_in_schema=False)
async def lender_view(token: str):
    """Serve the public lender HTML page (token is handled client-side)."""
    return FileResponse(os.path.join(static_dir, "lender.html"))


@app.get("/owner/{token}", include_in_schema=False)
async def owner_view(token: str):
    """Serve the owner portal HTML page."""
    return FileResponse(os.path.join(static_dir, "owner.html"))


@app.get("/report", include_in_schema=False)
async def report_view():
    """Serve the internal project status report page (auth required client-side)."""
    return FileResponse(os.path.join(static_dir, "report.html"))


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    _blocked = {"api/", "static/", "docs", "redoc", "openapi.json", "lender/", "report", "bid/", "co-approval/", "selections/", "prequal/", "subcontract/"}
    if any(full_path.startswith(b) or full_path == b for b in _blocked):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)
