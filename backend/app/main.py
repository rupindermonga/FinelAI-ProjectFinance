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
from .routes import auth, invoices, upload, columns, export, categories, admin, project, filetools, org, audit, pm, construction_health, compliance, lender_plus, lender_risk, permits, safety, labour, bid, ai_risk, co_approval, selections, equipment, notifications, lien_release, spec_review, prequalification, client_hub, syndicate, erp_integration, cfo_reports, subcontract, canadian_legal, quality, crm, assemblies, advanced_reports, lender_advanced, adjudication, gst_rebates, platform_api, phase11, bank_feed, execution_forecast


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
            # CRM
            """CREATE TABLE IF NOT EXISTS crm_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                company_name TEXT NOT NULL, contact_name TEXT, contact_email TEXT, contact_phone TEXT,
                project_type TEXT, estimated_value REAL, location TEXT,
                status TEXT DEFAULT 'prospect', source TEXT DEFAULT 'referral',
                probability_pct INTEGER DEFAULT 25, expected_close_date TEXT,
                notes TEXT, next_action TEXT, next_action_date TEXT,
                assigned_to INTEGER REFERENCES users(id),
                converted_project_id INTEGER REFERENCES projects(id),
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS proposal_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                lead_id INTEGER REFERENCES crm_leads(id) ON DELETE SET NULL,
                project_id INTEGER REFERENCES projects(id),
                proposal_number TEXT, title TEXT NOT NULL,
                client_name TEXT, client_email TEXT, client_address TEXT,
                valid_until TEXT, total_amount REAL,
                scope_of_work TEXT, inclusions TEXT, exclusions TEXT,
                payment_terms TEXT, warranty_period TEXT, notes TEXT,
                status TEXT DEFAULT 'draft',
                sign_token TEXT UNIQUE, signed_at DATETIME, signed_by_name TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_crm_leads_org ON crm_leads(org_id, status)",
            "CREATE INDEX IF NOT EXISTS ix_proposal_token ON proposal_packages(sign_token)",
            # Cost Assemblies
            """CREATE TABLE IF NOT EXISTS cost_assemblies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                name TEXT NOT NULL, description TEXT, trade_category TEXT, unit TEXT,
                usage_count INTEGER DEFAULT 0,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS cost_assembly_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assembly_id INTEGER NOT NULL REFERENCES cost_assemblies(id) ON DELETE CASCADE,
                division TEXT, description TEXT NOT NULL,
                quantity REAL, unit TEXT, unit_cost REAL, total_cost REAL,
                notes TEXT, display_order INTEGER DEFAULT 100
            )""",
            # Procurement
            """CREATE TABLE IF NOT EXISTS procurement_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                item_name TEXT NOT NULL, vendor_name TEXT, description TEXT,
                category TEXT DEFAULT 'other', lead_time_weeks INTEGER,
                order_date TEXT, required_on_site_date TEXT, delivery_date TEXT,
                quantity REAL, unit TEXT, unit_cost REAL, total_cost REAL,
                purchase_order_number TEXT,
                status TEXT DEFAULT 'to_order', delay_reason TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_procurement_project ON procurement_items(project_id, required_on_site_date)",
            # VE Log
            """CREATE TABLE IF NOT EXISTS ve_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                item_number TEXT, description TEXT NOT NULL,
                original_spec TEXT, proposed_alternate TEXT,
                original_cost REAL, alternate_cost REAL, potential_savings REAL,
                status TEXT DEFAULT 'proposed',
                accepted_by TEXT, decision_date TEXT,
                owner_approved INTEGER DEFAULT 0, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # CCDC Contracts
            """CREATE TABLE IF NOT EXISTS ccdc_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                ccdc_type TEXT NOT NULL, title TEXT, contract_value REAL,
                contractor_name TEXT, owner_name TEXT,
                execution_date TEXT, substantial_performance_date TEXT, final_completion_date TEXT,
                holdback_pct REAL DEFAULT 10, insurance_required INTEGER DEFAULT 1,
                bond_required INTEGER DEFAULT 0, supplementary_conditions TEXT,
                status TEXT DEFAULT 'draft', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS statutory_declarations_9a9b (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                ccdc_contract_id INTEGER REFERENCES ccdc_contracts(id) ON DELETE SET NULL,
                form_type TEXT NOT NULL,
                declarant_name TEXT, declarant_title TEXT, declarant_company TEXT,
                declaration_date TEXT, period_covered TEXT, amount_declared REAL,
                all_subs_paid INTEGER, outstanding_claims TEXT,
                commissioner_name TEXT, commissioner_date TEXT,
                status TEXT DEFAULT 'pending', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Unit Releases
            """CREATE TABLE IF NOT EXISTS unit_releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                unit_number TEXT NOT NULL, unit_type TEXT,
                floor_area_sf REAL, floor_number INTEGER,
                list_price REAL, sale_price REAL, buyer_name TEXT,
                deposit_amount REAL, deposit_received_date TEXT,
                purchase_agreement_date TEXT, closing_date TEXT,
                status TEXT DEFAULT 'available', incentives TEXT, notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Client Payment Schedules
            """CREATE TABLE IF NOT EXISTS client_payment_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                milestone_name TEXT NOT NULL, description TEXT,
                amount REAL, percentage_of_contract REAL,
                due_date TEXT, invoice_date TEXT, paid_date TEXT,
                status TEXT DEFAULT 'pending', notes TEXT, display_order INTEGER DEFAULT 100,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Specialized Checklists
            """CREATE TABLE IF NOT EXISTS specialized_checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                checklist_type TEXT NOT NULL, category TEXT, item_name TEXT NOT NULL,
                description TEXT, responsible_party TEXT, due_date TEXT,
                status TEXT DEFAULT 'pending', notes TEXT, completed_at DATETIME,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_unit_releases_project ON unit_releases(project_id)",
            "CREATE INDEX IF NOT EXISTS ix_ccdc_contracts_project ON ccdc_contracts(project_id)",
            "CREATE INDEX IF NOT EXISTS ix_specialized_checklist_project ON specialized_checklist_items(project_id, checklist_type)",
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
            # Phase 10: QS Inspector Reports
            """CREATE TABLE IF NOT EXISTS qs_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                report_date TEXT NOT NULL,
                qs_firm TEXT, qs_contact TEXT,
                overall_pct_complete REAL, cost_to_complete REAL, contingency_remaining REAL,
                schedule_status TEXT DEFAULT 'on_track',
                schedule_delay_weeks INTEGER, deficiency_count INTEGER DEFAULT 0,
                deficiency_notes TEXT, recommendation TEXT DEFAULT 'approve',
                ai_summary TEXT, file_path TEXT,
                status TEXT DEFAULT 'submitted', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS qs_trade_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL REFERENCES qs_reports(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                trade_name TEXT NOT NULL, csi_division TEXT,
                budget_amount REAL, cost_to_date REAL, cost_to_complete REAL,
                pct_complete REAL, status TEXT DEFAULT 'on_track',
                deficiencies TEXT, display_order INTEGER DEFAULT 100
            )""",
            "CREATE INDEX IF NOT EXISTS ix_qs_reports_project ON qs_reports(project_id, report_date)",
            # Phase 10: Adjudication Cases
            """CREATE TABLE IF NOT EXISTS adjudication_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                case_number TEXT, province TEXT DEFAULT 'ON',
                claimant_name TEXT NOT NULL, respondent_name TEXT NOT NULL,
                disputed_amount REAL, description TEXT,
                notice_date TEXT, adjudication_notice_date TEXT,
                adjudicator_name TEXT, adjudicator_appointed_date TEXT,
                determination_deadline TEXT, determination_date TEXT,
                determination_amount REAL, outcome TEXT,
                related_nnp_id INTEGER REFERENCES non_payment_notices(id),
                status TEXT DEFAULT 'initiated', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS adjudication_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL REFERENCES adjudication_cases(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                doc_type TEXT NOT NULL, title TEXT NOT NULL,
                submitted_by TEXT, submit_date TEXT, file_path TEXT, notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_adjudication_project ON adjudication_cases(project_id)",
            # Phase 10: Mezz Tranches
            """CREATE TABLE IF NOT EXISTS mezz_tranches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                tranche_name TEXT NOT NULL, tranche_type TEXT DEFAULT 'senior',
                lender_name TEXT, commitment_amount REAL, drawn_amount REAL DEFAULT 0,
                interest_rate REAL, interest_type TEXT DEFAULT 'fixed',
                draw_trigger TEXT, priority_rank INTEGER DEFAULT 1,
                maturity_date TEXT, currency TEXT DEFAULT 'CAD', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_mezz_tranches_project ON mezz_tranches(project_id, priority_rank)",
            # Phase 10: CMHC Take-out Conversion
            """CREATE TABLE IF NOT EXISTS takeout_conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                program TEXT DEFAULT 'CMHC MLI Select',
                permanent_lender TEXT, permanent_loan_amount REAL, permanent_rate REAL,
                amortization_years INTEGER, expected_conversion_date TEXT,
                actual_conversion_date TEXT, stabilization_period_end TEXT,
                target_occupancy_pct REAL, actual_occupancy_pct REAL,
                dscr_at_stabilization REAL, final_cost_certification_date TEXT,
                final_cost_certified_by TEXT,
                status TEXT DEFAULT 'construction', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            # Phase 10: Loan Pre-Funding Closing Checklist
            """CREATE TABLE IF NOT EXISTS loan_closing_checklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category TEXT NOT NULL, item_name TEXT NOT NULL, description TEXT,
                responsible_party TEXT, required_by TEXT, received_date TEXT, expiry_date TEXT,
                status TEXT DEFAULT 'outstanding', notes TEXT, display_order INTEGER DEFAULT 100,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_loan_closing_project ON loan_closing_checklist(project_id, category)",
            # Phase 10: GST/HST Rebate Applications
            """CREATE TABLE IF NOT EXISTS gst_rebate_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                rebate_type TEXT NOT NULL, cra_form TEXT, unit_address TEXT, unit_number TEXT,
                applicant_name TEXT, purchase_price REAL, gst_paid REAL, hst_paid REAL,
                eligible_amount REAL, rebate_pct REAL, estimated_rebate REAL,
                submitted_date TEXT, cra_reference TEXT, refund_received_date TEXT, refund_amount REAL,
                province TEXT DEFAULT 'ON', is_purpose_built_rental INTEGER DEFAULT 0,
                notes TEXT, status TEXT DEFAULT 'calculating',
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_gst_rebates_project ON gst_rebate_applications(project_id)",
            # Phase 10: API Keys
            """CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                name TEXT NOT NULL, key_prefix TEXT NOT NULL, key_hash TEXT NOT NULL,
                scopes TEXT DEFAULT 'read', last_used_at DATETIME, expires_at DATETIME,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_api_keys_org ON api_keys(org_id, is_active)",
            # Phase 10: Webhooks
            """CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                name TEXT NOT NULL, url TEXT NOT NULL, secret TEXT,
                events TEXT NOT NULL, is_active INTEGER DEFAULT 1,
                failure_count INTEGER DEFAULT 0, last_triggered_at DATETIME,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_id INTEGER NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                event TEXT NOT NULL, payload TEXT,
                http_status INTEGER, response_body TEXT, duration_ms INTEGER,
                success INTEGER DEFAULT 0, attempt_count INTEGER DEFAULT 1,
                delivered_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_webhooks_org ON webhooks(org_id)",
            # Phase 10: EFT Batches
            """CREATE TABLE IF NOT EXISTS eft_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                batch_number TEXT NOT NULL, value_date TEXT NOT NULL,
                total_amount REAL DEFAULT 0, payment_count INTEGER DEFAULT 0,
                originator_id TEXT, bank_name TEXT,
                status TEXT DEFAULT 'draft', file_path TEXT, notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS eft_batch_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES eft_batches(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER REFERENCES projects(id),
                vendor_id INTEGER REFERENCES org_vendors(id),
                invoice_id INTEGER REFERENCES invoices(id),
                payee_name TEXT NOT NULL,
                payee_bank_transit TEXT, payee_bank_institution TEXT, payee_bank_account TEXT,
                amount REAL NOT NULL, memo TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_eft_batches_org ON eft_batches(org_id, status)",
            # Bank Feed
            """CREATE TABLE IF NOT EXISTS bank_feed_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                provider TEXT DEFAULT 'flinks',
                institution_name TEXT, account_name TEXT, account_type TEXT, masked_account TEXT,
                flinks_login_id TEXT, flinks_request_id TEXT,
                status TEXT DEFAULT 'pending',
                last_synced_at DATETIME, balance REAL, currency TEXT DEFAULT 'CAD', notes TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS bank_feed_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL REFERENCES bank_feed_connections(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                transaction_date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_after REAL, raw_description TEXT, transaction_type TEXT, reference_number TEXT,
                ai_vendor_suggestion TEXT, ai_category_suggestion TEXT,
                ai_invoice_id INTEGER, ai_confidence TEXT, ai_reasoning TEXT,
                matched_invoice_id INTEGER REFERENCES invoices(id),
                matched_vendor_id INTEGER REFERENCES org_vendors(id),
                matched_category_id INTEGER REFERENCES cost_categories(id),
                status TEXT DEFAULT 'unmatched', notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS ix_bank_feed_transactions_org ON bank_feed_transactions(org_id, status, transaction_date)",
            # Execution Forecast — generic construction progress tracking
            """CREATE TABLE IF NOT EXISTS wf_workstreams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'units',
                display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS wf_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                sd_code TEXT,
                node_code TEXT NOT NULL,
                node_name TEXT,
                vendor TEXT,
                display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS wf_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                node_id INTEGER NOT NULL REFERENCES wf_nodes(id) ON DELETE CASCADE,
                workstream_id INTEGER NOT NULL REFERENCES wf_workstreams(id),
                vendor TEXT,
                start_date TEXT,
                deadline TEXT,
                total_scope REAL DEFAULT 0,
                remaining REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS wf_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES wf_tasks(id) ON DELETE CASCADE,
                org_id INTEGER NOT NULL REFERENCES organizations(id),
                project_id INTEGER NOT NULL REFERENCES projects(id),
                period TEXT NOT NULL,
                period_type TEXT DEFAULT 'monthly',
                planned_qty REAL DEFAULT 0,
                actual_qty REAL,
                entered_by INTEGER REFERENCES users(id),
                entered_at DATETIME,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, period)
            )""",
            "CREATE INDEX IF NOT EXISTS ix_wf_tasks_project ON wf_tasks(project_id, node_id)",
            "CREATE INDEX IF NOT EXISTS ix_wf_progress_project ON wf_progress(project_id, period)",
            "CREATE INDEX IF NOT EXISTS ix_wf_nodes_project ON wf_nodes(project_id, sd_code)",
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


def _normalize_gemini_keys():
    """Ensure GEMINI_API_KEY (singular) reflects the round-robin next key from GEMINI_API_KEYS.
    All Phase 10-12 routes read the singular key; this call is made once at startup
    so the key is always available. Runtime rotation is handled by get_gemini_key()."""
    multi = os.getenv("GEMINI_API_KEYS", "")
    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        if keys and not os.getenv("GEMINI_API_KEY", ""):
            os.environ["GEMINI_API_KEY"] = keys[0]


@asynccontextmanager
async def lifespan(app: FastAPI):
    _normalize_gemini_keys()
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
app.include_router(crm.router)
app.include_router(crm._public_router)
app.include_router(assemblies.router)
app.include_router(advanced_reports.router)
app.include_router(lender_advanced.router)
app.include_router(adjudication.router)
app.include_router(gst_rebates.router)
app.include_router(platform_api.router)
app.include_router(phase11.router)
app.include_router(bank_feed.router)
app.include_router(execution_forecast.router)

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
    """Serve the owner portal — uses the main SPA which handles /owner/ routing."""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/report", include_in_schema=False)
async def report_view():
    """Serve the internal project status report page (auth required client-side)."""
    return FileResponse(os.path.join(static_dir, "report.html"))


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    _blocked = {"api/", "static/", "docs", "redoc", "openapi.json", "lender/", "report", "bid/", "co-approval/", "selections/", "prequal/", "subcontract/", "proposal/"}
    if any(full_path.startswith(b) or full_path == b for b in _blocked):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)
