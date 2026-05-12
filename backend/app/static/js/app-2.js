const API = '';  // same origin — v2

function app() {
  return {
    // ── Auth ──────────────────────────────────────────────────────
    view: 'landing',
    authTab: 'login',
    authLoading: false,
    authError: '',
    loginForm: { username: '', password: '' },
    regForm: { username: '', email: '', password: '' },
    user: null,
    token: null,
    demoLoading: false,
    demoError: '',
    resetToken: '',
    inviteToken: '',

    // ── Audit log ─────────────────────────────────────────────────
    auditLog: [], auditTotal: 0, auditPage: 1, auditLoading: false,

    // ── AI Accountant ─────────────────────────────────────────────
    healthData: null, healthLoading: false,

    // ── Cash Flow ─────────────────────────────────────────────────
    cashFlowData: null, cashFlowLoading: false,

    // ── Canadian Compliance ───────────────────────────────────────
    vendorCompliance: null, vendorComplianceLoading: false,
    selectedVendorCompliance: null, showVendorComplianceModal: false,
    vendorComplianceForm: {},
    t5018Data: null, t5018Loading: false, t5018Year: new Date().getFullYear()-1,

    // ── Cost-to-Complete ──────────────────────────────────────────
    ctcData: null, ctcLoading: false,

    // ── Pay Readiness ─────────────────────────────────────────────
    payReadiness: null, payReadinessLoading: false,

    // ── Contract Matching ─────────────────────────────────────────
    contractMatching: null, contractMatchingLoading: false,

    // ── Prompt Payment ────────────────────────────────────────────
    promptPayment: null,

    // ── Funding Conditions ────────────────────────────────────────
    drawConditions: [], showConditionModal: false,
    conditionForm: { description:'', condition_type:'document', required_by:'' },
    activeDrawForConditions: null,

    // ── Draw Certificates ─────────────────────────────────────────
    drawCertificates: [], showCertModal: false,
    certForm: { cert_type:'progress', certifier_name:'', certifier_firm:'', cert_date:'', amount_certified:'' },
    activeDrawForCerts: null,

    // ── Owner Tokens ──────────────────────────────────────────────
    ownerTokens: [], showOwnerTokenModal: false,
    ownerTokenForm: { label:'', expires_at:'' },

    // ── Funding Conditions ────────────────────────────────────────
    drawConditions: [], showConditionModal: false,
    conditionForm: { description:'', condition_type:'document', required_by:'' },
    activeDrawForConditions: null,

    // ── Draw Certificates ─────────────────────────────────────────
    drawCertificates: [], showCertModal: false,
    certForm: { cert_type:'progress', certifier_name:'', certifier_firm:'', cert_date:'', amount_certified:'' },
    activeDrawForCerts: null,

    // ── Statutory Declarations ────────────────────────────────────
    drawDeclarations: [], showDeclModal: false,
    declForm: { vendor_name:'', declaration_date:'', period_end:'', amount:'' },
    activeDrawForDecls: null,

    // ── Owner Tokens ──────────────────────────────────────────────
    ownerTokens: [], showOwnerTokenModal: false,
    ownerTokenForm: { label:'', expires_at:'' },

    // ── PM state ──────────────────────────────────────────────────
    pmSummary: null,
    // Tasks
    pmTasks: [], pmTasksLoading: false,
    pmTaskFilter: { status: '', assigned_to: '' },
    showTaskModal: false, editingTask: null,
    taskForm: { title:'', description:'', task_type:'task', status:'not_started',
                priority:'medium', assigned_to:null, start_date:'', end_date:'',
                due_date:'', percent_complete:0, location:'', tags:'' },
    taskComments: [], taskCommentsLoading: false, newComment: '',
    showTaskDetail: false, selectedTask: null,
    // Daily logs
    pmDailyLogs: [], pmDailyLogsLoading: false,
    showDailyLogModal: false,
    dailyLogForm: { log_date:'', weather:'sunny', temperature:'', crew_count:0,
                    work_summary:'', issues:'', delays:'', visitors:'' },
    // RFIs
    pmRFIs: [], pmRFIsLoading: false,
    showRFIModal: false, editingRFI: null,
    rfiForm: { rfi_number:'', subject:'', description:'', priority:'medium',
               assigned_to:null, due_date:'', response:'' },
    // Punch list
    pmPunchItems: [], pmPunchLoading: false,
    showPunchModal: false, editingPunch: null,
    punchForm: { title:'', description:'', location:'', priority:'medium',
                 assigned_to:null, due_date:'' },
    // Submittals
    pmSubmittals: [], pmSubmittalsLoading: false,
    showSubmittalModal: false,
    submittalForm: { title:'', spec_section:'', status:'draft',
                     submitted_date:'', reviewer:null, review_notes:'' },
    // Meetings
    pmMeetings: [], pmMeetingsLoading: false,
    showMeetingModal: false, editingMeeting: null,
    meetingForm: { title:'', meeting_date:'', location:'', attendees:'',
                   agenda:'', minutes:'', action_items:'', next_meeting:'' },
    // Photos
    pmPhotos: [], pmPhotosLoading: false,

    // ── Safety Management ──────────────────────────────────────────
    safetyIncidents: [], safetyLoading: false,
    safetySummary: null,
    showSafetyModal: false, safetyEditId: null,
    safetyForm: { incident_date:'', incident_type:'near_miss', severity:'low', description:'', location:'', persons_involved:'', immediate_actions:'', wsib_reportable:false, mol_reportable:false, status:'open' },
    toolboxTalks: [], toolboxLoading: false,
    showToolboxModal: false, toolboxEditId: null,
    toolboxForm: { talk_date:'', topic:'', facilitator:'', attendee_count:0, attendees:'', duration_minutes:'', notes:'' },

    // ── Permits ────────────────────────────────────────────────────
    permitsData: [], permitsLoading: false,
    showPermitModal: false, permitEditId: null,
    permitForm: { permit_type:'building', permit_number:'', description:'', authority:'', application_date:'', issued_date:'', expiry_date:'', status:'pending', fee_paid:'', notes:'' },
    permitFormError: '',
    showPermitInspModal: false, activePermitForInsp: null,
    permitInspections: [],
    inspForm: { inspection_type:'', result:'pending', scheduled_date:'', completed_date:'', inspector_name:'', deficiencies:'' },

    // ── Warranty ───────────────────────────────────────────────────
    warrantyItems: [], warrantyLoading: false,
    showWarrantyModal: false, warrantyEditId: null,
    warrantyForm: { category:'other', description:'', location:'', reported_date:'', warranty_type:'1year', homeowner_name:'', status:'open', assigned_to:'', scheduled_date:'', notes:'' },

    // ── Labour / Timecards ─────────────────────────────────────────
    timecards: [], timecardsLoading: false,
    labourReport: null,
    showTimecardModal: false, timecardEditId: null,
    timecardForm: { worker_name:'', trade:'', classification:'', work_date:'', regular_hours:8, overtime_hours:0, double_time_hours:0, hourly_rate:'', burden_pct:30, work_description:'' },

    // ── WIP Report ─────────────────────────────────────────────────
    wipData: null, wipLoading: false,

    // ── Covenants ──────────────────────────────────────────────────
    covenantsData: [], covenantsLoading: false,
    showCovenantModal: false, covenantEditId: null,
    covenantForm: { covenant_type:'ltc', name:'', threshold_value:'', threshold_operator:'<=', current_value:'', as_of_date:'', status:'compliant', notes:'' },

    // ── Interest Reserve ───────────────────────────────────────────
    interestReserve: null, irLoading: false,
    showIRModal: false, irForm: { reserve_amount:'', interest_rate:'', accrual_basis:'actual/365', notes:'' },
    showIRDrawModal: false, irDrawForm: { draw_date:'', amount:'', period_start:'', period_end:'', notes:'' },

    // ── Bonds ──────────────────────────────────────────────────────
    bondsData: [], bondsLoading: false,
    showBondModal: false, bondEditId: null,
    bondForm: { vendor_name:'', bond_type:'performance', bond_number:'', surety_company:'', bond_amount:'', effective_date:'', expiry_date:'', status:'active', notes:'' },

    // ── Bid Management ─────────────────────────────────────────────
    bidPackages: [], bidPkgsLoading: false,
    showBidPkgModal: false, bidPkgEditId: null,
    bidPkgForm: { title:'', trade_category:'', issue_date:'', due_date:'', estimated_value:'', status:'draft', description:'', notes:'' },
    activeBidPackage: null,
    bidResponses: [], bidLeveling: null,
    showBidRespModal: false, bidRespEditId: null,
    bidRespForm: { vendor_name:'', contact_email:'', total_amount:'', inclusions:'', exclusions:'', qualifications:'', status:'invited', notes:'' },

    // ── Portfolio Risk ─────────────────────────────────────────────
    portfolioRisk: null, portfolioRiskLoading: false,

    // ── AI Risk Score ──────────────────────────────────────────────
    aiRiskData: null, aiRiskLoading: false,

    // ── Notifications ──────────────────────────────────────────────
    notifData: null, notifLoading: false,

    // ── Equipment ──────────────────────────────────────────────────
    equipList: [], equipLoading: false,
    equipUtilization: null,
    showEquipModal: false, equipEditId: null,
    equipForm: { name:'', equipment_type:'', make:'', model:'', year:'', ownership:'owned', daily_rate:'', hourly_rate:'', status:'available', notes:'' },
    showEquipLogModal: false, activeEquip: null, equipLogs: [],
    equipLogForm: { log_date:'', log_type:'usage', hours_used:0, fuel_litres:'', operator_name:'', work_description:'', cost:'', notes:'' },

    // ── Lien Releases ──────────────────────────────────────────────
    lienReleases: [], lienReleasesLoading: false,
    lienSummary: null,
    showLienReleaseModal: false, lienReleaseEditId: null,
    lienReleaseForm: { release_type:'progressive', vendor_name:'', holdback_amount:'', last_supply_date:'', lien_expiry_date:'', status:'lien_period_running', statutory_declaration_received:false, notes:'' },

    // ── Vendor Scorecard ───────────────────────────────────────────
    vendorScores: [], vendorScoresLoading: false,
    showVendorScoreModal: false, vendorScoreEditId: null,
    vendorScoreForm: { vendor_name:'', period:'', quality:null, timeliness:null, safety:null, communication:null, value:null, would_rehire:null, comments:'' },

    // ── Client Selections ──────────────────────────────────────────
    selectionItems: [], selectionsLoading: false,
    selSummary: null, selTokens: [],
    showSelModal: false, selEditId: null,
    selForm: { item_name:'', category_id:'', standard_option:'', client_choice:'', allowance_amount:'', actual_cost:'', upgrade_amount:'', status:'pending', due_date:'', notes:'' },

    // ── Cash Flow S-Curve ──────────────────────────────────────────
    scurveData: null, scurveLoading: false,

    // ── Loan Syndication ───────────────────────────────────────────
    syndicates: [], syndicatesLoading: false,
    showSyndicateModal: false, syndicateEditId: null,
    syndicateForm: { facility_name:'', total_commitment:'', currency:'CAD', lead_lender:'', closing_date:'', maturity_date:'', interest_rate:'', notes:'' },
    showParticipantModal: false,
    addParticipantForm: { syndicate_id:null, lender_name:'', participation_pct:'', contact_email:'', reporting_email:'' },
    activeSyndicateDrawReport: null,

    // ── ERP Integrations ───────────────────────────────────────────
    erpTypes: [], erpCredentials: [],
    erpTesting: null,
    showERPSetupModal: false, erpSetupType: null,
    erpSetupForm: { label:'', endpoint_url:'', credentials:{} },

    // ── AI Schedule Generation ─────────────────────────────────────
    generatedSchedule: null, aiSchedLoading: false,

    // ── CRM ────────────────────────────────────────────────────────
    crmLeads: [], crmLoading: false, crmPipeline: null, crmStatusFilter: null,
    showLeadModal: false, leadEditId: null,
    leadForm: { company_name:'', contact_name:'', contact_email:'', contact_phone:'', project_type:'commercial', estimated_value:'', location:'', status:'prospect', source:'referral', probability_pct:25, expected_close_date:'', next_action:'', notes:'' },
    allProposals: [], proposalsLoading: false,

    // ── Cost Assemblies ────────────────────────────────────────────
    assemblies: [], assembliesLoading: false,
    showAssemblyModal: false,
    assemblyForm: { name:'', description:'', trade_category:'', unit:'' },
    activeAssembly: null, assemblyItems: [],
    showAssemblyItemModal: false,
    asmItemForm: { division:'', description:'', quantity:'', unit:'', unit_cost:'', total_cost:'' },

    // ── Procurement ─────────────────────────────────────────────────
    procurementItems: [], procurementLoading: false,
    showProcurementModal: false, procEditId: null,
    procForm: { item_name:'', vendor_name:'', category:'other', lead_time_weeks:'', order_date:'', required_on_site_date:'', total_cost:'', status:'to_order', notes:'' },

    // ── VE Log ──────────────────────────────────────────────────────
    veItems: [], veLoading: false, veSummary: null,
    showVEModal: false, veEditId: null,
    veForm: { description:'', original_spec:'', proposed_alternate:'', original_cost:'', alternate_cost:'', status:'proposed', notes:'' },

    // ── CCDC ────────────────────────────────────────────────────────
    ccdcContracts: [], ccdcLoading: false,
    showCCDCModal: false, ccdcEditId: null,
    ccdcForm: { ccdc_type:'CCDC2', title:'', contract_value:'', contractor_name:'', owner_name:'', execution_date:'', holdback_pct:10, insurance_required:true, bond_required:false, status:'draft', notes:'' },

    // ── Units ────────────────────────────────────────────────────────
    unitData: null, unitsLoading: false,
    showUnitModal: false, unitEditId: null,
    unitForm: { unit_number:'', unit_type:'2br', floor_area_sf:'', floor_number:'', list_price:'', status:'available', notes:'' },

    // ── Client Payments ─────────────────────────────────────────────
    clientPayments: [], clientPaymentsLoading: false,
    showCPModal: false, cpEditId: null,
    cpForm: { milestone_name:'', amount:'', percentage_of_contract:'', due_date:'', status:'pending', notes:'' },

    // ── AI Spec Tools ───────────────────────────────────────────────
    specToolTab: 'qa',
    specQAQuestion: '', specQAContext: '', specQAResult: null, specQALoading: false,
    rfiGenerateIssue: '', rfiGenerateResult: null, rfiGenerateLoading: false,
    submittalGenResult: null, submittalGenLoading: false,

    // ── Advanced Reports ────────────────────────────────────────────
    advReportView: 'tax-reference',
    advReportData: null, advReportLoading: false,
    cashForecastData: null, forecastAccuracyData: null,

    // ── CFO Reports ────────────────────────────────────────────────
    cfoReportView: 'backlog',
    cfoData: null, cfoLoading: false,
    aiLenderMemoData: null, aiLenderMemoLoading: false,
    lenderMemoForm: { draw_amount:'', draw_number:'', notes:'' },

    // ── Subcontracts ───────────────────────────────────────────────
    subcontracts: [], subcontractsLoading: false,
    showSubcontractModal: false, subcontractEditId: null,
    subcontractForm: { vendor_name:'', trade:'', contract_amount:'', holdback_pct:10, payment_terms:'Net 30 — progress draws', start_date:'', end_date:'', scope_of_work:'', inclusions:'', exclusions:'', insurance_required:true, bond_required:false, warranty_period:'1 year from Substantial Performance', notes:'' },

    // ── Sources & Uses ─────────────────────────────────────────────
    sourcesUses: null, sourcesUsesLoading: false,
    showSUModal: false, suEditId: null,
    suForm: { entry_type:'source', category:'equity', description:'', budgeted_amount:'', actual_amount:'', as_of_date:'', notes:'' },

    // ── Estimating ─────────────────────────────────────────────────
    estimates: [], estimatesLoading: false,
    activeEstimate: null, estimateItems: [], estimateDivisions: {},
    showEstimateModal: false, showEstimateItemModal: false,
    estimateForm: { name:'', description:'' },
    estItemForm: { division:'', description:'', quantity:'', unit:'', unit_cost:'', total_cost:'', subcontracted:false, notes:'' },
    estItemEditId: null,

    // ── Canadian Legal ─────────────────────────────────────────────
    legalTab: 'proper-invoice',
    nnpList: [], spCerts: [],
    showNNPModal: false, nnpEditId: null,
    nnpForm: { payment_type:'gc_to_sub', vendor_name:'', proper_invoice_date:'', certifier_cert_date:'', disputed_amount:'', non_disputed_amount:'', reasons:'', notice_date:'', notes:'' },
    showSPModal: false, spEditId: null,
    spForm: { contract_amount:'', certified_amount:'', holdback_amount:'', certification_date:'', publication_date:'', consultant_name:'', consultant_firm:'', owner_name:'', contractor_name:'', notes:'' },
    invoiceValidationResult: null, invoiceToValidate: '',

    // ── Quality Inspections ────────────────────────────────────────
    qualityInspections: [], qualityLoading: false,
    activeInspection: null, inspectionItems: [],
    showQIModal: false,
    qiForm: { inspection_date:'', inspector_name:'', area_location:'', inspection_type:'rough_framing', notes:'' },

    // ── Visitor Log ────────────────────────────────────────────────
    visitors: [], visitorsLoading: false,
    showVisitorModal: false, visitorEditId: null,
    visitorForm: { visit_date:'', visitor_name:'', visitor_company:'', visitor_type:'other', purpose:'', host_name:'', time_in:'', time_out:'', badge_number:'', safety_orientation:false, notes:'' },

    // ── Sub Prequalification ───────────────────────────────────────
    prequals: [], prequalsLoading: false,

    // ── Client Hub ─────────────────────────────────────────────────
    hubPosts: [], hubMessages: [],
    hubNewMessage: '',
    showHubPostModal: false,
    hubPostForm: { title:'', body:'', milestone:'', visibility:'client' },

    // ── Drawing Register ───────────────────────────────────────────
    drawings: [], drawingsLoading: false,
    showDrawingModal: false, drawingEditId: null,
    drawingForm: { drawing_number:'', title:'', discipline:'Architectural', current_revision:'Rev 0', revision_date:'', status:'issued', notes:'' },

    // ── AI Spec Review ─────────────────────────────────────────────
    specReviews: [], specReviewLoading: false,

    // ── Union Compliance ───────────────────────────────────────────
    unions: [], unionsLoading: false,
    showUnionModal: false, unionEditId: null,
    unionForm: { trade:'', local_number:'', agreement_type:'iba', apprentice_ratio:'1:4', journeymen_count:0, apprentice_count:0, expiry_date:'', notes:'' },

    // ── Project Closeout ───────────────────────────────────────────
    closeoutItems: [], closeoutLoading: false,
    closeoutSummary: null,
    showCloseoutModal: false,
    closeoutForm: { category:'documents', item_name:'', responsible_party:'', due_date:'', status:'pending', notes:'' },

    // ── Execution Forecast ────────────────────────────────────────
    efTab: 'grid',                   // 'grid' | 'actuals' | 'summary' | 'import'
    efImporting: false, efImportResult: null, efImportFile: null,
    efGrid: [], efPeriods: [],        // full plan vs actual table
    efSummary: [], efSummaryPeriods: [],
    efFilterSD: '', efFilterPeriod: '',
    efSDs: [],                        // available subdivisions
    efActualsPeriod: '', efActualsEntries: [], efActualsSaving: false,
    efWorkstreams: [], efNodes: [],   // master lists for manual entry
    efShowAddNode: false, efShowAddWS: false,
    efNewNode: { sd_code:'', node_code:'', vendor:'' },
    efNewWS: { name:'', unit:'km' },

    // ── Bank Feed (Flinks + AI Matching) ─────────────────────────
    bankFeedConnections: [], bankFeedTxns: [], bankFeedFilter: 'unmatched',
    bankFeedUnmatched: 0, showBankFeedModal: false, flinksLoginId: false,
    bankFeedForm: { institution_name:'', account_name:'', account_type:'chequing', masked_account:'', flinks_login_id:'' },
    aiMatchLoading: false, aiMatchResult: null,
    // ── Phase 11: Bank Import ─────────────────────────────────────
    bankFile: null, bankParsing: false, bankDetected: null,
    bankTransactions: [], bankMatches: [],
    // ── Phase 11: FX / Currency ───────────────────────────────────
    fxRates: null, fxLoading: false,
    fxAmount: 1000, fxFromCurrency: 'USD', fxResult: null,
    // ── Phase 11: Stress Testing ──────────────────────────────────
    stressParams: { reserve_amount:'', drawn_to_date:'', loan_balance:'', interest_rate:5.5, months_remaining:12, current_pre_sales_pct:0 },
    stressResults: null, stressLoading: false,
    // ── Mobile / GPS ──────────────────────────────────────────────
    gpsLoading: false, gpsLocation: null, gpsCoords: null,
    mobileTimecardOpen: false,
    mobileTC: { worker_name:'', trade:'', work_date:new Date().toISOString().slice(0,10), regular_hours:8, work_description:'' },
    mobileTCLoading: false, mobileTCSuccess: false,

    // ── Phase 10: QS Reports ──────────────────────────────────────
    qsReports: [], showQSModal: false, qsEditId: null,
    qsForm: { report_date:'', qs_firm:'', overall_pct_complete:'', cost_to_complete:'', recommendation:'approve', schedule_status:'on_track', schedule_delay_weeks:'', deficiency_count:0, deficiency_notes:'', notes:'' },
    showQSAIParseModal: false, qsAIFile: null, qsAIParsing: false, qsAIResult: null,
    // ── Phase 10: Mezz Tranches ───────────────────────────────────
    mezzData: null, showMezzModal: false, mezzEditId: null,
    mezzForm: { tranche_name:'', tranche_type:'senior', lender_name:'', commitment_amount:'', drawn_amount:0, interest_rate:'', interest_type:'fixed', priority_rank:1, maturity_date:'', draw_trigger:'', notes:'' },
    // ── Phase 10: CMHC Take-out ───────────────────────────────────
    takeoutData: null, showTakeoutModal: false,
    takeoutForm: { program:'CMHC MLI Select', permanent_lender:'', permanent_loan_amount:'', permanent_rate:'', amortization_years:'', expected_conversion_date:'', target_occupancy_pct:'', dscr_at_stabilization:'', status:'construction', notes:'' },
    // ── Phase 10: Loan Closing Checklist ──────────────────────────
    loanClosingItems: [], loanClosingSummary: null, showLoanClosingModal: false,
    loanClosingForm: { category:'zoning', item_name:'', description:'', required_by:'', status:'outstanding', notes:'' },
    // ── Phase 10: GST/HST Rebates ────────────────────────────────
    gstRebates: [], showGSTModal: false, gstEditId: null,
    gstForm: { rebate_type:'new_housing', province:'ON', applicant_name:'', unit_address:'', purchase_price:'', gst_paid:'', status:'calculating', refund_amount:'' },
    gstCalc: { rebate_type:'new_housing', purchase_price:'', gst_paid:'', province:'ON', is_purpose_built_rental:false }, gstCalcResult: null,
    // ── Phase 10: EFT Batches ─────────────────────────────────────
    eftBatches: [], showEFTModal: false,
    eftForm: { batch_number:'', value_date:'', bank_name:'', originator_id:'', notes:'' },
    // ── Phase 10: API Keys ────────────────────────────────────────
    apiKeys: [], newAPIKey: null,
    // ── Phase 10: Webhooks ────────────────────────────────────────
    webhooks: [], showWebhookModal: false, newWebhookSecret: null,
    webhookForm: { name:'', url:'', events:'invoice.created' },
    // ── Phase 10: Adjudication ────────────────────────────────────
    adjudications: [], showAdjModal: false, adjEditId: null,
    adjForm: { case_number:'', province:'ON', claimant_name:'', respondent_name:'', disputed_amount:'', status:'initiated', adjudicator_name:'', adjudicator_appointed_date:'', description:'' },
    // ── Phase 10: Doc Q&A ─────────────────────────────────────────
    docQAQuestion: '', docQAAnswer: null, docQALoading: false, docQASources: [],
    docQASuggestions: ['Which RFIs are still open?', 'What delays were reported this week?', 'When was the last draw approved?', 'What change orders are pending owner approval?'],
    // ── Phase 10: AI Client Update ────────────────────────────────
    clientUpdateText: null, clientUpdateLoading: false, clientUpdateTone: 'professional', clientUpdateMeta: null,
    // ── Loan closing categories ───────────────────────────────────
    get loanClosingCategories() { return [...new Set((this.loanClosingItems||[]).map(i=>i.category))]; },

    // ── Super Admin UI ────────────────────────────────────────────
    showCreateOrgModal: false,
    createOrgForm: { name: '', owner_username: '', plan: 'starter' },
    createOrgLoading: false, createOrgError: '',
    showOrgMembersModal: false,
    orgMembersList: [],
    selectedOrgForAdmin: null,
    showSuperAdminInviteModal: false,
    saInviteEmail: '', saInviteRole: 'editor',
    saInviteLoading: false, saInviteMsg: '', saInviteErr: false,

    // ── Org invite UI ─────────────────────────────────────────────
    showInvitePanel: false,
    inviteForm: { email: '', role: 'editor' },
    inviteLoading: false, inviteMsg: '', inviteError: '',
    pendingInvites: [],

    // ── Mobile sidebar ────────────────────────────────────────────
    sidebarOpen: false,

    // ── Organisation (multi-tenant) ───────────────────────────────
    orgs: [],
    currentOrg: null,
    orgMembers: [],
    orgVendors: [],
    showOrgModal: false,          // create org modal
    showMemberModal: false,
    showVendorModal: false,
    orgForm: { name: '', slug: '' },
    orgFormError: '',
    orgFormLoading: false,
    memberForm: { username: '', role: 'editor' },
    memberFormError: '',
    memberFormLoading: false,
    availableRoles: [],   // loaded from /api/org/roles
    vendorForm: { vendor_code: '', name: '', trade: '', contact_name: '', contact_email: '', contact_phone: '', payment_terms: '', hst_number: '', notes: '' },
    vendorFormError: '',
    vendorFormLoading: false,
    editingVendorId: null,
    orgVendorSearch: '',
    allOrgsList: [],              // super-admin: all orgs

    // ── Multi-project ──────────────────────────────────────────────
    projects: [],
    currentProject: null,
    showNewProjectModal: false,
    newProjectForm: { name: '', code: '', client: '', address: '', start_date: '', end_date: '', total_budget: 0, lender_budget: null, currency: 'CAD', project_type: 'custom' },
    newProjectError: '',
    newProjectLoading: false,

    // ── Invoices ──────────────────────────────────────────────────
    invoices: [],
    stats: {},
    filters: { start_date: '', end_date: '', vendor: '', currency: '', status: '', draw_id: '', claim_id: '' },
    exportDates: { start: '', end: '' },
    exportMode: 'summary',
    pagination: { page: 1, limit: 50, total: 0, pages: 0 },
    viewMode: 'summary',   // 'summary' | 'lines'

    // ── Upload ────────────────────────────────────────────────────
    showUploadModal: false,
    uploadFiles: [],
    uploadLoading: false,
    uploadError: '',
    isDragging: false,

    // ── Invoice detail ────────────────────────────────────────────
    showInvoiceDetail: false,
    selectedInvoice: null,
    activeDetailTab: 'fields',   // 'fields' | 'preview'
    previewUrl: null,
    previewType: null,           // 'pdf' | 'image'
    previewLoading: false,
    editingInvoice: false,
    editBuffer: {},
    editSaving: false,

    // ── Columns ───────────────────────────────────────────────────
    allColumns: [],
    activeColumns: [],
    get viewableColumns() { return this.activeColumns.filter(c => c.is_viewable !== false); },
    showAddColumnModal: false,
    editingColumn: null,
    columnForm: { field_key: '', field_label: '', field_description: '', field_type: 'string', display_order: 100 },
    columnFormError: '',
    columnFormLoading: false,

    // ── Processing queue (SSE) ────────────────────────────────────
    processingQueue: [],
    sseSource: null,

    // ── Settings / Admin API Keys ─────────────────────────────────
    adminApiKeys: [],
    showApiKeyModal: false,
    apiKeyForm: { label: '', key_value: '', priority: 100, is_active: true },
    apiKeyFormError: '',
    apiKeyFormLoading: false,
    settingsSaved: false,

    // ── Categories ────────────────────────────────────────────────
    categoryTree: [],
    selectedCategory: null,
    selectedSubCategory: null,
    showAddCategoryModal: false,
    addCategoryLevel: 'category',
    addCategoryParent: null,
    addCategoryName: '',
    addCategoryError: '',
    addCategoryLoading: false,


    // ── Project Finance ──────────────────────────────────────────
    projectDash: null,
    financeInvoices: [],
    financeInvoiceFilter: 'all',
    costCategories: [],
    subdivisions: [],
    selectedAllocInvoice: null,
    allocations: [],
    allocForm: { category_id: '', sub_category_id: '', subdivision_id: '', percentage: 100 },
    showAllocModal: false,
    showPaymentModal: false,
    paymentForm: { invoice_id: null, amount: '', payment_date: '', method: '', reference: '', notes: '' },
    invoicePayments: [],

    // ── Payroll ───────────────────────────────────────────────────
    payrollEntries: [],
    showPayrollModal: false,
    payrollForm: { employee_name: '', company_name: '', pay_period_start: '', pay_period_end: '', gross_pay: 0, cpp: 0, ei: 0, income_tax: 0, insurance: 0, holiday_pay: 0, other_deductions: 0, working_days: 22, statutory_holidays: 0, province: 'ON' },
    payrollFormError: '',
    editingPayrollId: null,

    // ── Upload draw/claim selection (persisted) ─────────────────
    uploadDrawId: localStorage.getItem('lastDrawId') || '',
    uploadProvClaimId: localStorage.getItem('lastProvClaimId') || '',
    uploadFedClaimId: localStorage.getItem('lastFedClaimId') || '',

    // ── Vendor Mapping ────────────────────────────────────────
    vendorSummary: [],
    reclassifying: false,
    reclassifyResult: null,

    // ── File Tools ─────────────────────────────────────────────
    finderInvoices: [],
    finderSourceFolder: localStorage.getItem('finderSourceFolder') || '',
    finderOutputFolder: '',
    finderSearching: false,
    finderResults: null,
    bulkFolderPath: localStorage.getItem('bulkFolderPath') || '',
    bulkUploading: false,
    bulkResults: null,

    // ── Cash Flow ─────────────────────────────────────────────────
    cashFlow: null,
    cashFlowLoading: false,

    // ── Budget view toggle ────────────────────────────────────────
    budgetView: 'internal',   // 'internal' | 'lender'

    // ── Portfolio / Aged Payables ─────────────────────────────────
    portfolio: null,
    agedPayables: null,

    async loadPortfolio() {
      try { this.portfolio = await this.get('/api/project/portfolio'); } catch(e) {}
    },

    async loadAgedPayables() {
      try { this.agedPayables = await this.get(`/api/project/aged-payables${this._pid}`); } catch(e) {}
    },

    downloadAccountingExport(format) {
      const pid = this.currentProject ? '?project_id=' + this.currentProject.id + '&format=' + format : '?format=' + format;
      const link = document.createElement('a');
      link.href = '/api/project/export/accounting-csv' + pid;
      link.download = `invoices_${format}.csv`;
      link.click();
    },

    async downloadLenderPackage(drawId, drawNumber) {
      const btn = event?.currentTarget;
      if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i>Building…'; }
      try {
        const res = await fetch(`/api/project/draws/${drawId}/lender-package-pdf`, {
          headers: { Authorization: 'Bearer ' + this.token }
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'PDF generation failed' }));
          throw new Error(err.detail || 'PDF generation failed');
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Draw_${drawNumber}_Lender_Package.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      } catch(e) {
        alert('Error generating package: ' + e.message);
      } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-file-pdf mr-1"></i>Package'; }
      }
    },

    // ── Milestones ────────────────────────────────────────────────
    milestones: [],
    showMsModal: false,
    msForm: { name:'', description:'', target_date:'', actual_date:'', pct_complete:0, status:'pending' },
    msFormError: '',
    msFormLoading: false,
    editingMsId: null,

    async loadMilestones() {
      try { this.milestones = await this.get(`/api/project/milestones${this._pid}`); } catch(e) {}
    },

    async saveMs() {
      if (!this.msForm.name.trim()) { this.msFormError = 'Name required'; return; }
      this.msFormLoading = true; this.msFormError = '';
      try {
        const payload = { ...this.msForm, pct_complete: parseFloat(this.msForm.pct_complete) || 0 };
        if (this.editingMsId) await this.put(`/api/project/milestones/${this.editingMsId}`, payload);
        else await this.post(`/api/project/milestones${this._pid}`, payload);
        this.showMsModal = false; this.editingMsId = null;
        this.msForm = { name:'', description:'', target_date:'', actual_date:'', pct_complete:0, status:'pending' };
        await this.loadMilestones();
      } catch(e) { this.msFormError = e.message || 'Save failed'; }
      finally { this.msFormLoading = false; }
    },

    async deleteMs(id) {
      if (!confirm('Delete this milestone?')) return;
      await this.del(`/api/project/milestones/${id}`);
      await this.loadMilestones();
    },

    // ── Lien Waivers ──────────────────────────────────────────────
    lienWaivers: [],
    showLwModal: false,
    lwForm: { vendor_name:'', waiver_type:'conditional', draw_id:'', subcontractor_id:'', amount:'', date_received:'', notes:'' },
    lwFormError: '',
    lwFormLoading: false,

    async loadLienWaivers() {
      try { this.lienWaivers = await this.get(`/api/project/lien-waivers${this._pid}`); } catch(e) {}
    },

    async saveLw() {
      if (!this.lwForm.vendor_name?.trim() && !this.lwForm.subcontractor_id) { this.lwFormError = 'Vendor name or subcontractor required'; return; }
      if (!this.lwForm.waiver_type) { this.lwFormError = 'Waiver type required'; return; }
      this.lwFormLoading = true; this.lwFormError = '';
      try {
        const payload = { ...this.lwForm, amount: this.lwForm.amount ? parseFloat(this.lwForm.amount) : null, draw_id: this.lwForm.draw_id || null, subcontractor_id: this.lwForm.subcontractor_id || null };
        await this.post(`/api/project/lien-waivers${this._pid}`, payload);
        this.showLwModal = false;
        this.lwForm = { vendor_name:'', waiver_type:'conditional', draw_id:'', subcontractor_id:'', amount:'', date_received:'', notes:'' };
        await this.loadLienWaivers();
      } catch(e) { this.lwFormError = e.message || 'Save failed'; }
      finally { this.lwFormLoading = false; }
    },

    async deleteLw(id) {
      if (!confirm('Delete this lien waiver record?')) return;
      await this.del(`/api/project/lien-waivers/${id}`);
      await this.loadLienWaivers();
    },

    // ── Documents ─────────────────────────────────────────────────
    documents: [],
    docTypeFilter: 'all',
    showDocModal: false,
    docForm: { title:'', doc_type:'contract', notes:'', draw_id:'', category_id:'', external_url:'' },
    docFile: null,
    docFormError: '',
    docFormLoading: false,

    async loadDocuments() {
      try { this.documents = await this.get(`/api/project/documents${this._pid}`); } catch(e) {}
    },

    async uploadDocument() {
      if (!this.docForm.title.trim()) { this.docFormError = 'Title required'; return; }
      this.docFormLoading = true; this.docFormError = '';
      try {
        const fd = new FormData();
        fd.append('title', this.docForm.title);
        fd.append('doc_type', this.docForm.doc_type);
        if (this.docForm.notes) fd.append('notes', this.docForm.notes);
        if (this.docForm.draw_id) fd.append('draw_id', this.docForm.draw_id);
        if (this.docForm.category_id) fd.append('category_id', this.docForm.category_id);
        if (this.docForm.external_url) fd.append('external_url', this.docForm.external_url);
        if (this.docFile) fd.append('file', this.docFile);
        const pid = this.currentProject ? '?project_id=' + this.currentProject.id : '';
        const res = await fetch('/api/project/documents/upload' + pid, { method:'POST', headers:{Authorization:'Bearer '+this.token}, body:fd });
        if (!res.ok) { const e=await res.json(); throw new Error(e.detail||'Upload failed'); }
        this.showDocModal = false;
        this.docFile = null;
        this.docForm = { title:'', doc_type:'contract', notes:'', draw_id:'', category_id:'', external_url:'' };
        await this.loadDocuments();
      } catch(e) { this.docFormError = e.message; }
      finally { this.docFormLoading = false; }
    },

    async deleteDocument(id) {
      if (!confirm('Delete this document?')) return;
      await this.del(`/api/project/documents/${id}`);
      await this.loadDocuments();
    },

    // ── Lender Tokens ─────────────────────────────────────────────
    lenderTokens: [],
    showLenderTokenModal: false,
    lenderTokenForm: { label: '', draw_id: '', expires_at: '' },
    lenderTokenError: '',
    lenderTokenLoading: false,

    async loadLenderTokens() {
      try { this.lenderTokens = await this.get(`/api/project/lender-tokens${this._pid}`); } catch(e) {}
    },

    async createLenderToken() {
      if (!this.lenderTokenForm.label.trim()) { this.lenderTokenError = 'Label required'; return; }
      this.lenderTokenLoading = true; this.lenderTokenError = '';
      try {
        const payload = { label: this.lenderTokenForm.label, draw_id: this.lenderTokenForm.draw_id ? parseInt(this.lenderTokenForm.draw_id) : null, expires_at: this.lenderTokenForm.expires_at || null };
        const t = await this.post(`/api/project/lender-tokens${this._pid}`, payload);
        this.lenderTokenForm = { label: '', draw_id: '', expires_at: '' };
        this.showLenderTokenModal = false;
        await this.loadLenderTokens();
        const url = window.location.origin + '/lender/' + t.token;
        prompt('Shareable lender link (copy this):', url);
      } catch(e) { this.lenderTokenError = e.message || 'Failed'; }
      finally { this.lenderTokenLoading = false; }
    },

    async toggleLenderToken(id) {
      await this.put(`/api/project/lender-tokens/${id}/toggle`, {});
      await this.loadLenderTokens();
    },

    async deleteLenderToken(id) {
      if (!confirm('Revoke and delete this link?')) return;
      await this.del(`/api/project/lender-tokens/${id}`);
      await this.loadLenderTokens();
    },

    copyLenderLink(token) {
      const url = window.location.origin + '/lender/' + token;
      navigator.clipboard?.writeText(url).then(() => alert('Link copied to clipboard!')).catch(() => prompt('Copy this link:', url));
    },

    // ── Subcontractors ────────────────────────────────────────────
    subcontractors: [],
    showSubModal: false,
    subForm: { name:'', trade:'', contact_name:'', contact_email:'', contact_phone:'', contract_value:'', status:'active', insurance_expiry:'', wsib_expiry:'', notes:'' },
    subFormError: '',
    subFormLoading: false,
    editingSubId: null,

    // ── Holdback & Approvals ──────────────────────────────────────
    holdbackFilter: 'outstanding',
    approvalFilter: 'pending',

    // ── Committed Costs ───────────────────────────────────────────
    showCcModal: false,
    ccForm: { vendor: '', description: '', contract_amount: 0, status: 'active', category_id: '', contract_date: '', expected_completion: '', notes: '' },
    ccFormError: '',
    ccFormLoading: false,
    editingCcId: null,

    // ── Change Orders ─────────────────────────────────────────────
    showCoModal: false,
    coForm: { co_number: '', description: '', amount: 0, status: 'pending', category_id: '', issued_by: '', date: '', notes: '' },
    coFormError: '',
    coFormLoading: false,
    editingCoId: null,

    // ── Draws & Claims ──────────────────────────────────────────
    financeView: 'draws',    // 'draws' | 'provincial' | 'federal'
    draws: [],
    claims: [],
    showDrawModal: false,
    drawForm: { draw_number: '', fx_rate: 1.0, submission_date: '', status: 'draft', notes: '' },
    drawFormError: '',
    editingDrawId: null,
    showClaimModal: false,
    claimForm: { claim_number: '', claim_type: 'provincial', fx_rate: 1.0, submission_date: '', status: 'draft', notes: '' },
    claimFormError: '',
    editingClaimId: null,
    showAssignInvoicesModal: false,
    assignTarget: null,       // { type: 'draw'|'claim', id, number }
    assignableInvoices: [],
    assignedInvoiceIds: [],
    fxRateLoading: false,

    // ── AI Intelligence ───────────────────────────────────────────
    aiInsights: null,
    aiLoading: false,
    aiError: '',
    aiActiveTab: 'compliance',    // compliance | overruns | draws | cashflow | subs | lender | mapper
    // Cash flow simulator sliders
    cfDelayMonths: 0,
    cfInflationPct: 0,
    cfDrawDelay: 0,
    cfScenario: null,
    cfScenarioLoading: false,
    // Draw readiness
    drawReadiness: {},            // keyed by draw_id
    drawReadinessLoading: false,
    // AI mapper
    aiSuggestion: null,
    aiSuggestionLoading: false,
    aiSuggestionInvoiceId: null,
    // Feature 8: draw approval scores (keyed by draw_id)
    drawApprovalScores: {},
    drawApprovalLoading: false,
    // Feature 9: closeout (in aiInsights.closeout)
    // Feature 10: govt optimizer (in aiInsights.govt_optimizer)
    // Feature 11: cost consultant
    costConsultant: null,
    costConsultantLoading: false,
    // Feature 12: CO radar (in aiInsights.co_radar)
    // Feature 13: vendor risk (in aiInsights.vendor_risk)

    async loadAiInsights() {
      if (!this.currentProject) return;
      this.aiLoading = true; this.aiError = '';
      try {
        this.aiInsights = await this.get(`/api/project/ai/insights${this._pid}`);
      } catch(e) { this.aiError = e.message || 'AI insights unavailable'; }
      finally { this.aiLoading = false; }
    },

    async loadDrawReadiness(drawId) {
      this.drawReadinessLoading = true;
      try {
        this.drawReadiness[drawId] = await this.get(`/api/project/ai/draw-readiness/${drawId}`);
      } catch(e) { this.drawReadiness[drawId] = { error: e.message }; }
      finally { this.drawReadinessLoading = false; }
    },

    async loadCfScenario() {
      if (!this.currentProject) return;
      this.cfScenarioLoading = true;
      try {
        const params = `${this._pid}&delay_months=${this.cfDelayMonths}&cost_inflation_pct=${this.cfInflationPct}&draw_delay_days=${this.cfDrawDelay}`;
        const sep = this._pid ? '&' : '?';
        const url = `/api/project/ai/cashflow-scenarios${this._pid}${sep.replace('?','&')}delay_months=${this.cfDelayMonths}&cost_inflation_pct=${this.cfInflationPct}&draw_delay_days=${this.cfDrawDelay}`;
        this.cfScenario = await this.get(`/api/project/ai/cashflow-scenarios?project_id=${this.currentProject.id}&delay_months=${this.cfDelayMonths}&cost_inflation_pct=${this.cfInflationPct}&draw_delay_days=${this.cfDrawDelay}`);
      } catch(e) {}
      finally { this.cfScenarioLoading = false; }
    },

    async aiSuggestAllocation(invoiceId) {
      this.aiSuggestionLoading = true; this.aiSuggestion = null; this.aiSuggestionInvoiceId = invoiceId;
      try {
        const payload = { invoice_id: invoiceId, project_id: this.currentProject?.id || null };
        this.aiSuggestion = await this.post('/api/project/ai/suggest-allocation', payload);
      } catch(e) { this.aiSuggestion = { error: e.message || 'AI suggestion failed' }; }
      finally { this.aiSuggestionLoading = false; }
    },

    async acceptAiSuggestion() {
      if (!this.aiSuggestion || !this.aiSuggestion.category_id) return;
      if (!this.selectedAllocInvoice) return;
      // Pre-fill the alloc form with the suggestion
      this.allocForm.category_id = String(this.aiSuggestion.category_id);
      if (this.aiSuggestion.sub_category_id) this.allocForm.sub_category_id = String(this.aiSuggestion.sub_category_id);
      this.allocForm.percentage = 100;
      this.aiSuggestion = null;
    },

    aiSeverityColor(sev) {
      const map = { critical: 'red', high: 'orange', warning: 'yellow', info: 'blue', low: 'green', medium: 'yellow' };
      const c = map[sev] || 'slate';
      return `bg-${c}-50 border-${c}-200 text-${c}-800`;
    },

    aiSeverityBadge(sev) {
      const map = { critical: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', warning: 'bg-yellow-100 text-yellow-700', info: 'bg-blue-100 text-blue-700', low: 'bg-green-100 text-green-700', medium: 'bg-yellow-100 text-yellow-700' };
      return map[sev] || 'bg-slate-100 text-slate-700';
    },

    async loadDrawApprovalScore(drawId) {
      this.drawApprovalLoading = true;
      try {
        this.drawApprovalScores[drawId] = await this.get(`/api/project/ai/draw-approval-score/${drawId}`);
      } catch(e) { this.drawApprovalScores[drawId] = { error: e.message }; }
      finally { this.drawApprovalLoading = false; }
    },

    async loadCostConsultant() {
      if (!this.currentProject) return;
      this.costConsultantLoading = true; this.costConsultant = null;
      try {
        this.costConsultant = await this.get(`/api/project/ai/cost-consultant${this._pid}`);
      } catch(e) { this.costConsultant = { error: e.message }; }
      finally { this.costConsultantLoading = false; }
    },

    riskBadge(level) {
      const map = { critical: 'bg-red-100 text-red-700 border border-red-200', high: 'bg-orange-100 text-orange-700 border border-orange-200', medium: 'bg-yellow-100 text-yellow-700 border border-yellow-200', low: 'bg-green-100 text-green-700 border border-green-200' };
      return map[level] || 'bg-slate-100 text-slate-600';
    },

    // ── Init ──────────────────────────────────────────────────────
    async init() {
      // Migrate lineItemColumns: add any new columns not in saved config
      const savedLI = JSON.parse(localStorage.getItem('lineItemColumns') || 'null');
      if (savedLI) {
        const savedKeys = new Set(savedLI.map(c => c.key));
        if (!savedKeys.has('cost_sub_category'))
          savedLI.push({ key: 'cost_sub_category', label: 'Sub-Category', active: true, visible: true, exportable: true });
        if (!savedKeys.has('cost_category'))
          savedLI.splice(savedLI.findIndex(c => c.key === 'sub_division') + 1, 0, { key: 'cost_category', label: 'Category', active: true, visible: true, exportable: true });
        if (!savedKeys.has('olt_id'))
          savedLI.push({ key: 'olt_id', label: 'OLT', active: true, visible: true, exportable: true });
        this.lineItemColumns = savedLI;
        localStorage.setItem('lineItemColumns', JSON.stringify(this.lineItemColumns));
      }

      const path = window.location.pathname.replace(/^\//, '');

      // ── Dedicated /demo route — auto-launch demo ──────────────────
      if (path === 'demo') {
        this.demoLoading = true;
        try {
          const res = await fetch('/api/auth/demo', { method: 'POST' });
          if (!res.ok) { this.view = 'landing'; window.location.href = '/'; return; }
          const data = await res.json();
          // setAuth without touching URL (we stay at /demo)
          this.token = data.access_token;
          this.user = data.user;
          this.orgs = data.orgs || [];
          const savedOrgId = parseInt(localStorage.getItem('currentOrgId'));
          this.currentOrg = (savedOrgId && this.orgs.find(o => o.id === savedOrgId))
            || (data.active_org_id && this.orgs.find(o => o.id === data.active_org_id))
            || this.orgs[0] || null;
          // Do NOT save demo token to localStorage — demo is session-only
          this.view = 'dashboard';
          await this.loadProjects();
          await Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()]);
        } catch(e) { window.location.href = '/'; }
        this.demoLoading = false;
        return;
      }

      // ── Deep-link routes ─────────────────────────────────────────
      if (path === 'reset-password') { this.resetToken = new URLSearchParams(window.location.search).get('token') || ''; this.view = 'reset-password'; return; }
      if (path === 'signup') { this.view = 'signup'; return; }
      if (path === 'accept-invite') { this.inviteToken = new URLSearchParams(window.location.search).get('token') || ''; this.view = 'accept-invite'; return; }

      // ── Auto-login from saved token (real accounts only) ─────────
      const saved = localStorage.getItem('invoice_token');
      const savedUser = localStorage.getItem('invoice_user');
      // Purge any stale demo token that was incorrectly saved to localStorage
      if (saved && savedUser) {
        try {
          const u = JSON.parse(savedUser);
          if (u?.is_demo || u?.username === 'demo') {
            localStorage.removeItem('invoice_token');
            localStorage.removeItem('invoice_user');
            localStorage.removeItem('currentOrgId');
            this.view = 'landing';
            return;
          }
        } catch(e) {}
      }
      if (saved && savedUser) {
        // Clean any deep-link URL (forgot-password, etc.) — always go back to root
        if (window.location.pathname !== '/') history.replaceState({}, '', '/');
        this.token = saved;
        this.user = JSON.parse(savedUser);
        try {
          this.orgs = await this.get('/api/org');
          const savedOrgId = parseInt(localStorage.getItem('currentOrgId'));
          this.currentOrg = (savedOrgId && this.orgs.find(o => o.id === savedOrgId)) || this.orgs[0] || null;
        } catch(e) {
          // Token likely expired — clear storage and show marketing page
          localStorage.removeItem('invoice_token');
          localStorage.removeItem('invoice_user');
          localStorage.removeItem('currentOrgId');
          this.view = 'landing';
          return;
        }
        // Restore view from URL path if valid
        const urlView = window.location.pathname.replace(/^\//, '').replace(/\//g, '-') || 'dashboard';
        const ROUTABLE = new Set(['dashboard','invoices','finance','columns','categories','budget-vs-actual',
          'holdback','approvals','cashflow','finance-summary','draws','claims','lender','lender-risk',
          'compliance','pm-tasks','pm-daily-logs','pm-rfis','pm-punch','pm-submittals','pm-meetings',
          'pm-photos','construction-health','permits','safety','labour','bid-packages','co-approval',
          'selections','equipment','notifications','lien-release','spec-review','prequalification',
          'client-hub','syndicate','erp-integrations','cfo-reports','subcontractors','canadian-legal',
          'quality','crm','assemblies','advanced-reports','lender-advanced','adjudication','gst-rebates',
          'platform-api','eft-batches','api-keys','webhooks','bank-feed','bank-import','fx-rates',
          'stress-test','execution-forecast','audit-log','org','vendor-directory','superadmin']);
        this.view = ROUTABLE.has(urlView) ? urlView : 'dashboard';
        history.replaceState({}, '', '/' + this.view);

        await this.loadProjects();
        await Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()]);
        if (this.user?.is_admin) await this.loadApiKeys();

      }
      // Otherwise: stay on landing page (view defaults to 'landing')
    },


    // ── Auth ──────────────────────────────────────────────────────
    async login() {
      this.authLoading = true;
      this.authError = '';
      try {
        const res = await this.post('/api/auth/login', this.loginForm, false);
        this.setAuth(res);
      } catch (e) {
        this.authError = e.message;
      } finally {
        this.authLoading = false;
      }
    },

    async register() {
      this.authLoading = true;
      this.authError = '';
      try {
        const res = await this.post('/api/auth/register', this.regForm, false);
        this.setAuth(res);
      } catch (e) {
        this.authError = e.message;
      } finally {
        this.authLoading = false;
      }
    },

    setAuth(data) {
      this.token = data.access_token;
      this.user = data.user;
      // Set org context from login response
      this.orgs = data.orgs || [];
      const savedOrgId = parseInt(localStorage.getItem('currentOrgId'));
      this.currentOrg = (savedOrgId && this.orgs.find(o => o.id === savedOrgId))
        || (data.active_org_id && this.orgs.find(o => o.id === data.active_org_id))
        || this.orgs[0] || null;
      localStorage.setItem('invoice_token', this.token);
      localStorage.setItem('invoice_user', JSON.stringify(this.user));
      if (this.currentOrg) localStorage.setItem('currentOrgId', this.currentOrg.id);
      // Clean URL — remove any deep-link path (forgot-password, etc.) after login
      if (window.location.pathname !== '/') history.replaceState({}, '', '/');
      this.view = 'dashboard';
      this.loadProjects().then(() => {
        Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()])
          .then(() => {
            if (this.user?.is_admin) this.loadApiKeys();
            if ((this.stats.pending || 0) > 0 || (this.stats.errors || 0) > 0) {
              this.retryErrorInvoices();
            }
          });
      });
    },

    switchOrg(org) {
      this.currentOrg = org;
      localStorage.setItem('currentOrgId', org.id);
      // Reset project-scoped state
      this.projects = []; this.currentProject = null; this.projectDash = null;
      this.financeInvoices = []; this.aiInsights = null;
      Promise.all([
        this.loadProjects(),
        this.loadInvoices(),
        this.loadStats(),
      ]);
    },

    logout() {
      const wasDemo = this.user?.is_demo;
      this.token = null; this.user = null;
      this.orgs = []; this.currentOrg = null;
      localStorage.removeItem('invoice_token');
      localStorage.removeItem('invoice_user');
      localStorage.removeItem('currentOrgId');
      if (this.sseSource) this.sseSource.close();
      // Demo sessions live at /demo — redirect to / on logout so URL is clean
      if (wasDemo || window.location.pathname.startsWith('/demo')) {
        window.location.href = '/';
      } else {
        this.view = 'landing';
      }
    },

    // ── Org management ────────────────────────────────────────────
    async loadOrgMembers() {
      try {
        [this.orgMembers, this.availableRoles] = await Promise.all([
          this.get('/api/org/members'),
          this.get('/api/org/roles'),
        ]);
      } catch(e) { this.orgMembers = []; }
    },

    async loadAllOrgs() {
      if (!this.user?.is_admin) return;
      try { this.allOrgsList = await this.get('/api/org/all'); } catch(e) {}
    },

    async adminJoinOrg(orgId, role) {
      try {
        await this.post(`/api/org/admin-join/${orgId}`, { role });
        await this.loadAllOrgs();
        // Refresh org list so new org appears in switcher
        const orgsResp = await this.get('/api/org');
        this.orgs = orgsResp;
        alert(`Joined org as ${role}. Switch to it using the org switcher.`);
      } catch(e) { alert('Failed: ' + e.message); }
    },

    async loadOrgVendors() {
      try { this.orgVendors = await this.get('/api/org/vendors'); } catch(e) {}
    },

    async createOrg() {
      if (!this.orgForm.name.trim()) { this.orgFormError = 'Name required'; return; }
      if (!this.orgForm.slug.trim()) { this.orgFormError = 'Slug required'; return; }
      this.orgFormLoading = true; this.orgFormError = '';
      try {
        const org = await this.post('/api/org', this.orgForm);
        this.orgs.push(org);
        this.showOrgModal = false;
        this.orgForm = { name: '', slug: '' };
        if (!this.currentOrg) this.switchOrg(org);
      } catch(e) { this.orgFormError = e.message; }
      finally { this.orgFormLoading = false; }
    },

    autoSlug() {
      this.orgForm.slug = this.orgForm.name.toLowerCase()
        .replace(/[^a-z0-9\s\-]/g, '').trim().replace(/\s+/g, '-').replace(/\-+/g, '-').slice(0, 48);
    },

    async addMember() {
      if (!this.memberForm.username.trim()) { this.memberFormError = 'Username required'; return; }
      this.memberFormLoading = true; this.memberFormError = '';
      try {
        await this.post('/api/org/members', this.memberForm);
        this.showMemberModal = false;
        this.memberForm = { username: '', role: 'editor' };
        await this.loadOrgMembers();
      } catch(e) { this.memberFormError = e.message; }
      finally { this.memberFormLoading = false; }
    },

    async updateMemberRole(memberId, role) {
      try { await this.put(`/api/org/members/${memberId}`, { role }); await this.loadOrgMembers(); } catch(e) { alert(e.message); }
    },

    async removeMember(memberId) {
      if (!confirm('Remove this member from the organization?')) return;
      try { await this.del(`/api/org/members/${memberId}`); await this.loadOrgMembers(); } catch(e) { alert(e.message); }
    },

    async saveVendor() {
      if (!this.vendorForm.name.trim()) { this.vendorFormError = 'Name required'; return; }
      this.vendorFormLoading = true; this.vendorFormError = '';
      try {
        const payload = { ...this.vendorForm };
        if (this.editingVendorId) await this.put(`/api/org/vendors/${this.editingVendorId}`, payload);
        else await this.post('/api/org/vendors', payload);
        this.showVendorModal = false; this.editingVendorId = null;
        this.vendorForm = { vendor_code: '', name: '', trade: '', contact_name: '', contact_email: '', contact_phone: '', payment_terms: '', hst_number: '', notes: '' };
        await this.loadOrgVendors();
      } catch(e) { this.vendorFormError = e.message; }
      finally { this.vendorFormLoading = false; }
    },

    async deleteVendor(id) {
      if (!confirm('Deactivate this vendor?')) return;
      try { await this.del(`/api/org/vendors/${id}`); await this.loadOrgVendors(); } catch(e) { alert(e.message); }
    },

    editVendor(v) {
      this.editingVendorId = v.id;
      this.vendorForm = { vendor_code: v.vendor_code||'', name: v.name, trade: v.trade||'', contact_name: v.contact_name||'', contact_email: v.contact_email||'', contact_phone: v.contact_phone||'', payment_terms: v.payment_terms||'', hst_number: v.hst_number||'', notes: v.notes||'' };
      this.showVendorModal = true;
    },

    get filteredOrgVendors() {
      if (!this.orgVendorSearch) return this.orgVendors;
      const s = this.orgVendorSearch.toLowerCase();
      return this.orgVendors.filter(v => (v.name||'').toLowerCase().includes(s) || (v.vendor_code||'').toLowerCase().includes(s) || (v.trade||'').toLowerCase().includes(s));
    },

    async loadAllOrgs() {
      try { this.allOrgsList = await this.get('/api/org/admin/all'); } catch(e) {}
    },

    async toggleOrgActive(orgId) {
      try { await this.put(`/api/org/admin/${orgId}/toggle`, {}); await this.loadAllOrgs(); } catch(e) { alert(e.message); }
    },

    roleBadge(role) {
      const m = { owner: 'bg-purple-100 text-purple-700', admin: 'bg-blue-100 text-blue-700', editor: 'bg-green-100 text-green-700', viewer: 'bg-gray-100 text-gray-600' };
      return m[role] || 'bg-gray-100 text-gray-600';
    },

    async loadProjects() {
      try {
        this.projects = await this.get('/api/project/list');
        const savedId = parseInt(localStorage.getItem('currentProjectId'));
        if (savedId && this.projects.find(p => p.id === savedId)) {
          this.currentProject = this.projects.find(p => p.id === savedId);
        } else {
          this.currentProject = this.projects[0] || null;
        }
      } catch (e) { console.error('loadProjects', e); }
    },

    switchProject(p) {
      this.currentProject = p;
      localStorage.setItem('currentProjectId', p.id);
      this.aiInsights = null; this.cfScenario = null; this.drawReadiness = {};
      Promise.all([
        this.loadProjectDashboard(),
        this.loadSubdivisions ? this.loadSubdivisions() : Promise.resolve(),
        this.loadPayroll(),
      ]);
      if (this.view === 'ai') this.loadAiInsights();
    },

    get _pid() {
      return this.currentProject ? `?project_id=${this.currentProject.id}` : '';
    },

    async createProject() {
      if (!this.newProjectForm.name.trim()) {
        this.newProjectError = 'Project name is required.'; return;
      }
      if (!this.newProjectForm.project_type) {
        this.newProjectError = 'Please select a project type.'; return;
      }
      this.newProjectLoading = true; this.newProjectError = '';
      try {
        const { project_type, ...body } = this.newProjectForm;
        const proj = await this.post(`/api/project?project_type=${project_type}`, body);
        this.projects.push(proj);
        this.currentProject = proj;
        localStorage.setItem('currentProjectId', proj.id);
        this.showNewProjectModal = false;
        this.newProjectForm = { name: '', code: '', client: '', address: '', start_date: '', end_date: '', total_budget: 0, lender_budget: null, currency: 'CAD', project_type: 'custom' };
        await Promise.all([this.loadProjectDashboard(), this.loadSubdivisions()]);
      } catch (e) {
        this.newProjectError = e.message || 'Failed to create project';
      } finally { this.newProjectLoading = false; }
    },

    async loadSubcontractors() {
      try { this.subcontractors = await this.get(`/api/project/subcontractors${this._pid}`); } catch(e) {}
    },

    async saveSub() {
      if (!this.subForm.name.trim()) { this.subFormError = 'Name is required.'; return; }
      this.subFormLoading = true; this.subFormError = '';
      try {
        const payload = { ...this.subForm, contract_value: this.subForm.contract_value ? parseFloat(this.subForm.contract_value) : null };
        if (this.editingSubId) {
          await this.put(`/api/project/subcontractors/${this.editingSubId}`, payload);
        } else {
          await this.post(`/api/project/subcontractors${this._pid}`, payload);
        }
        this.showSubModal = false; this.editingSubId = null;
        this.subForm = { name:'', trade:'', contact_name:'', contact_email:'', contact_phone:'', contract_value:'', status:'active', insurance_expiry:'', wsib_expiry:'', notes:'' };
        await this.loadSubcontractors();
      } catch(e) { this.subFormError = e.message || 'Save failed'; }
      finally { this.subFormLoading = false; }
    },

    async deleteSub(id) {
      if (!confirm('Delete this subcontractor?')) return;
      await this.del(`/api/project/subcontractors/${id}`);
      await this.loadSubcontractors();
    },

    async loadCashFlow() {
      this.cashFlowLoading = true;
      try {
        this.cashFlow = await this.get(`/api/project/cash-flow${this._pid}`);
      } catch (e) { console.error(e); }
      finally { this.cashFlowLoading = false; }
    },

    async releaseHoldback(invoiceId, undo = false) {
      try {
        const body = undo
          ? { holdback_released: false, holdback_released_date: null }
          : { holdback_released: true };
        await this.put(`/api/invoices/${invoiceId}/holdback`, body);
        // Update local invoice state
        const inv = this.invoices.find(i => i.id === invoiceId);
        if (inv) { inv.holdback_released = !undo; inv.holdback_released_date = undo ? null : new Date().toISOString().split('T')[0]; }
        await this.loadProjectDashboard();
      } catch (e) { alert('Failed: ' + e.message); }
    },

    async setApproval(invoiceId, status) {
      try {
        const data = await this.put(`/api/invoices/${invoiceId}/approval`, { approval_status: status });
        const inv = this.invoices.find(i => i.id === invoiceId);
        if (inv) { inv.approval_status = data.approval_status; inv.approved_by = data.approved_by; inv.approved_at = data.approved_at; }
        await this.loadProjectDashboard();
      } catch (e) { alert('Failed: ' + e.message); }
    },

    async bulkApproveByDraw() {
      const draw_id = this.uploadDrawId || prompt('Enter Draw ID to bulk-approve:');
      if (!draw_id) return;
      try {
        const data = await this.post('/api/invoices/bulk-approve', { draw_id: parseInt(draw_id) });
        alert(`Approved ${data.approved} invoices.`);
        await Promise.all([this.loadInvoices(), this.loadProjectDashboard()]);
      } catch (e) { alert('Failed: ' + e.message); }
    },

    async saveCc() {
      if (!this.ccForm.vendor.trim() || !this.ccForm.contract_amount) {
        this.ccFormError = 'Vendor and contract amount are required.'; return;
      }
      this.ccFormLoading = true; this.ccFormError = '';
      try {
        const payload = { ...this.ccForm, contract_amount: parseFloat(this.ccForm.contract_amount) || 0, category_id: this.ccForm.category_id || null };
        if (this.editingCcId) {
          await this.put(`/api/project/committed-costs/${this.editingCcId}`, payload);
        } else {
          await this.post(`/api/project/committed-costs${this._pid}`, payload);
        }
        this.showCcModal = false;
        this.editingCcId = null;
        this.ccForm = { vendor: '', description: '', contract_amount: 0, status: 'active', category_id: '', contract_date: '', expected_completion: '', notes: '' };
        await this.loadProjectDashboard();
      } catch (e) { this.ccFormError = e.message || 'Save failed'; }
      finally { this.ccFormLoading = false; }
    },

    async deleteCc(id) {
      if (!confirm('Delete this committed cost?')) return;
      await this.del(`/api/project/committed-costs/${id}`);
      await this.loadProjectDashboard();
    },

    async saveChangeOrder() {
      if (!this.coForm.co_number.trim() || !this.coForm.description.trim()) {
        this.coFormError = 'CO number and description are required.'; return;
      }
      this.coFormLoading = true; this.coFormError = '';
      try {
        const payload = { ...this.coForm, amount: parseFloat(this.coForm.amount) || 0, category_id: this.coForm.category_id || null };
        if (this.editingCoId) {
          await this.put(`/api/project/change-orders/${this.editingCoId}`, payload);
        } else {
          await this.post(`/api/project/change-orders${this._pid}`, payload);
        }
        this.showCoModal = false;
        this.editingCoId = null;
        this.coForm = { co_number: '', description: '', amount: 0, status: 'pending', category_id: '', issued_by: '', date: '', notes: '' };
        await this.loadProjectDashboard();
      } catch (e) { this.coFormError = e.message || 'Save failed'; }
      finally { this.coFormLoading = false; }
    },

    openEditCo(co) {
      this.editingCoId = co.id;
      this.coForm = { co_number: co.co_number, description: co.description, amount: co.amount, status: co.status, category_id: co.category_id || '', issued_by: co.issued_by || '', date: co.date || '', notes: co.notes || '' };
      this.coFormError = '';
      this.showCoModal = true;
    },

    async deleteCo(id) {
      if (!confirm('Delete this change order?')) return;
      await this.del(`/api/project/change-orders/${id}`);
      await this.loadProjectDashboard();
    },

    async tryDemo() {
      this.demoLoading = true;
      this.demoError = '';
      try {
        const res = await fetch('/api/auth/demo', { method: 'POST' });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Demo unavailable — please try again later.');
        }
        const data = await res.json();
        // Session-only — do NOT save to localStorage so real logins aren't overwritten
        this.token = data.access_token;
        this.user = data.user;
        this.orgs = data.orgs || [];
        this.currentOrg = this.orgs[0] || null;
        this.view = 'dashboard';
        await this.loadProjects();
        await Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()]);
      } catch (e) {
        this.demoError = e.message;
      } finally {
        this.demoLoading = false;
      }
    },


    // ── Invoices ──────────────────────────────────────────────────
    async loadInvoices() {
      const params = new URLSearchParams({ page: this.pagination.page, limit: this.pagination.limit });
      if (this.filters.start_date) params.set('start_date', this.filters.start_date);
      if (this.filters.end_date)   params.set('end_date',   this.filters.end_date);
      if (this.filters.vendor)     params.set('vendor',     this.filters.vendor);
      if (this.filters.currency)   params.set('currency',   this.filters.currency);
      if (this.filters.status)     params.set('status',     this.filters.status);
      if (this.filters.draw_id)    params.set('draw_id',    this.filters.draw_id);
      if (this.filters.claim_id)   params.set('claim_id',   this.filters.claim_id);

      try {
        const data = await this.get(`/api/invoices?${params}`);
        this.invoices = data.items;
        this.pagination = { ...this.pagination, total: data.total, pages: data.pages };
      } catch (e) { console.error(e); }
    },

    // ── URL routing — call go(view) from sidebar buttons ─────────────
    go(viewName, fn) {
      this.view = viewName;
      history.pushState({}, '', '/' + viewName);
      if (fn) fn();
    },

    async loadStats() {
      try {
        this.stats = await this.get('/api/invoices/stats');
        // Sync URL with current view on every stats load
        if (this.view && !['landing','login','forgot-password','reset-password','signup','accept-invite'].includes(this.view)) {
          history.replaceState({}, '', '/' + this.view);
        }
        if ((this.stats.pending || 0) > 0) {
          // Active processing — poll fast
          setTimeout(() => { this.loadStats(); this.loadInvoices(); }, 4000);
        } else {
          // Idle — refresh every 30s so newly uploaded invoices appear automatically
          setTimeout(() => { this.loadStats(); this.loadInvoices(); }, 30000);
        }
      } catch (e) {}
    },

    async retryErrorInvoices() {
      this.retryingInvoices = true;
      try {
        const r = await this.post('/api/invoices/retry-errors', {});
        // Start polling every 3 seconds automatically
        this._startProcessingPoll();
      } catch(e) { alert('Retry failed: ' + e.message); this.retryingInvoices = false; }
    },

    _startProcessingPoll() {
      const poll = async () => {
        await this.loadStats();
        await this.loadInvoices();
        const pending = this.stats.pending || 0;
        if (pending > 0) {
          setTimeout(poll, 3000);
        } else {
          this.retryingInvoices = false;
        }
      };
      setTimeout(poll, 2000);
    },

    clearFilters() {
      this.filters = { start_date: '', end_date: '', vendor: '', currency: '', status: '', draw_id: '', claim_id: '' };
      this.pagination.page = 1;
      this.loadInvoices();
    },

    changePage(delta) {
      this.pagination.page = Math.max(1, Math.min(this.pagination.pages, this.pagination.page + delta));
      this.loadInvoices();
    },

    openInvoice(inv) {
      this.selectedInvoice = inv;
      this.activeDetailTab = 'fields';
      this.editingInvoice = false;
      this.editBuffer = {};
      // Revoke any previous blob URL
      if (this.previewUrl) { URL.revokeObjectURL(this.previewUrl); this.previewUrl = null; }
      this.previewType = null;
      this.showInvoiceDetail = true;
    },

    closeInvoiceDetail() {
      if (this.previewUrl) { URL.revokeObjectURL(this.previewUrl); this.previewUrl = null; }
      this.editingInvoice = false;
      this.editBuffer = {};
      this.showInvoiceDetail = false;
    },

    startEditingInvoice() {
      if (!this.selectedInvoice) return;
      const data = this.selectedInvoice.extracted_data || {};
      this.editBuffer = {};
      for (const col of this.allColumns.filter(c => c.is_active && c.field_key !== 'line_items')) {
        const val = data[col.field_key] ?? this.selectedInvoice[col.field_key] ?? '';
        this.editBuffer[col.field_key] = val === null ? '' : String(val);
      }
      this.editingInvoice = true;
    },

    async saveInvoiceEdits() {
      if (!this.selectedInvoice) return;
      this.editSaving = true;
      try {
        // Build patch: only send changed fields
        const data = this.selectedInvoice.extracted_data || {};
        const patch = {};
        for (const [key, newVal] of Object.entries(this.editBuffer)) {
          const oldVal = String(data[key] ?? this.selectedInvoice[key] ?? '');
          if (newVal !== oldVal) {
            patch[key] = newVal === '' ? null : newVal;
          }
        }
        if (Object.keys(patch).length === 0) {
          this.editingInvoice = false;
          return;
        }
        await fetch(`/api/invoices/${this.selectedInvoice.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', ...this._headers() },
          body: JSON.stringify(patch),
        });
        // Refresh the invoice data
        const updated = await this.get(`/api/invoices/${this.selectedInvoice.id}`);
        const idx = this.invoices.findIndex(i => i.id === updated.id);
        if (idx !== -1) this.invoices[idx] = updated;
        this.selectedInvoice = updated;
        this.editingInvoice = false;
        this.editBuffer = {};
      } catch (e) {
        alert('Save failed: ' + e.message);
      } finally {
        this.editSaving = false;
      }
    },

    async switchToPreview() {
      this.activeDetailTab = 'preview';
      if (!this.previewUrl && !this.previewLoading) {
        await this.loadPreview();
      }
    },

    async loadPreview() {
      if (!this.selectedInvoice) return;
      this.previewLoading = true;
      try {
        const res = await fetch(`/api/invoices/${this.selectedInvoice.id}/file`, { headers: this._headers() });
        if (!res.ok) throw new Error('File not available on server');
        const blob = await res.blob();
        // Detect type: content-type header → blob.type → filename extension
        const ct = res.headers.get('content-type') || blob.type || '';
        const fname = (this.selectedInvoice.original_filename || '').toLowerCase();
        const imageExts = ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif'];
        const isImageExt = imageExts.some(e => fname.endsWith(e));
        this.previewType = (ct.startsWith('image/') || isImageExt) ? 'image' : 'pdf';
        this.previewUrl = URL.createObjectURL(blob);
      } catch (e) {
        alert('Cannot preview: ' + e.message);
        this.activeDetailTab = 'fields';
      } finally {
        this.previewLoading = false;
      }
    },

    async deleteInvoice(id) {
      if (!confirm('Delete this invoice? This cannot be undone.')) return;
      try {
        await this.del(`/api/invoices/${id}`);
        this.invoices = this.invoices.filter(i => i.id !== id);
        this.loadStats();
      } catch (e) { alert('Could not delete invoice: ' + e.message); }
    },

    async reprocessInvoice(inv) {
      if (!inv) return;
      try {
        await this.post(`/api/invoices/${inv.id}/reprocess`, {});
        inv.status = 'pending';
        this.loadStats();
        alert('Queued for re-extraction. The worker will pick it up within 10 seconds.');
      } catch (e) { alert('Could not queue for reprocessing: ' + e.message); }
    },

    // Line-items flat view: each line item becomes its own row
    // ── Line Item Column Config ──────────────────────────────────
    lineItemColumns: JSON.parse(localStorage.getItem('lineItemColumns') || 'null') || [
      { key: 'line_no', label: 'Line #', active: true, visible: true, exportable: true },
      { key: 'sku', label: 'SKU', active: true, visible: true, exportable: true },
      { key: 'description', label: 'Description', active: true, visible: true, exportable: true },
      { key: 'qty', label: 'Qty', active: true, visible: true, exportable: true },
      { key: 'unit', label: 'Unit', active: true, visible: true, exportable: true },
      { key: 'unit_price', label: 'Unit Price', active: true, visible: true, exportable: true },
      { key: 'discount_amount', label: 'Discount', active: true, visible: false, exportable: true },
      { key: 'tax_rate', label: 'Tax %', active: true, visible: false, exportable: true },
      { key: 'line_total', label: 'Line Total', active: true, visible: true, exportable: true },
      { key: 'manufacturer', label: 'Manufacturer', active: false, visible: false, exportable: true },
      { key: 'sub_division', label: 'Sub-Division', active: true, visible: true, exportable: true },
      { key: 'cost_category', label: 'Category', active: true, visible: true, exportable: true },
      { key: 'cost_sub_category', label: 'Sub-Category', active: true, visible: true, exportable: true },
      { key: 'olt_id', label: 'OLT', active: true, visible: true, exportable: true },
    ],
    get visibleLineItemCols() { return this.lineItemColumns.filter(c => c.active !== false && c.visible); },
    toggleLineItemCol(col, field) {
      col[field] = !col[field];
      localStorage.setItem('lineItemColumns', JSON.stringify(this.lineItemColumns));
    },

    get lineItemsFlat() {
      const TAX_RE = /^\s*(HST|GST|PST|QST|RST|HST\s*\(|GST\s*\/|sales\s*tax|tax\s+on)/i;
      const rows = [];
      for (const inv of this.invoices) {
        const items = inv.extracted_data?.line_items;
        if (Array.isArray(items) && items.length > 0) {
          const billable = items.filter(it => !TAX_RE.test(it.description || ''));
          for (const item of billable) {
            rows.push({ inv, item });
          }
        } else {
          rows.push({ inv, item: null });
        }
      }
      return rows;
    },


    // ── Columns ───────────────────────────────────────────────────
    async loadColumns() {
      try {
        this.allColumns = await this.get('/api/columns');
        this.activeColumns = this.allColumns.filter(c => c.is_active);
      } catch (e) { console.error(e); }
    },

    async toggleColumn(col) {
      try {
        const res = await this.put(`/api/columns/${col.id}/toggle`, {});
        col.is_active = res.is_active;
        this.activeColumns = this.allColumns.filter(c => c.is_active);
      } catch (e) { alert('Could not toggle column: ' + e.message); }
    },

    async toggleColumnExport(col) {
      try {
        const res = await this.put(`/api/columns/${col.id}/toggle-export`, {});
        col.is_exportable = res.is_exportable;
      } catch (e) { alert('Could not toggle export flag: ' + e.message); }
    },
    async toggleColumnView(col) {
      try {
        const res = await this.put(`/api/columns/${col.id}/toggle-view`, {});
        col.is_viewable = res.is_viewable;
      } catch (e) { alert('Could not toggle view flag: ' + e.message); }
    },
    async moveColumn(col, direction) {
      const idx = this.allColumns.indexOf(col);
      const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= this.allColumns.length) return;
      // Swap display_order values
      const tmp = this.allColumns[swapIdx].display_order;
      this.allColumns[swapIdx].display_order = col.display_order;
      col.display_order = tmp;
      // Swap positions in array
      [this.allColumns[idx], this.allColumns[swapIdx]] = [this.allColumns[swapIdx], this.allColumns[idx]];
      // Save to backend
      const order = this.allColumns.map((c, i) => ({ id: c.id, display_order: i }));
      try { await this.put('/api/columns/reorder', order); } catch(e) { console.warn(e); }
      this.activeColumns = this.allColumns.filter(c => c.is_active);
    },

    openEditColumn(col) {
      this.editingColumn = col;
      this.columnForm = {
        field_key: col.field_key,
        field_label: col.field_label,
        field_description: col.field_description || '',
        field_type: col.field_type,
        display_order: col.display_order,
      };
      this.columnFormError = '';
      this.showAddColumnModal = true;
    },

    closeColumnModal() {
      this.showAddColumnModal = false;
      this.editingColumn = null;
      this.columnForm = { field_key: '', field_label: '', field_description: '', field_type: 'string', display_order: 100 };
      this.columnFormError = '';
    },

    async saveColumn() {
      this.columnFormLoading = true;
      this.columnFormError = '';
      try {
        if (this.editingColumn) {
          const updated = await this.put(`/api/columns/${this.editingColumn.id}`, {
            field_label: this.columnForm.field_label,
            field_description: this.columnForm.field_description,
            field_type: this.columnForm.field_type,
            display_order: this.columnForm.display_order,
          });
          const idx = this.allColumns.findIndex(c => c.id === updated.id);
          if (idx !== -1) this.allColumns[idx] = updated;
        } else {
          const created = await this.post('/api/columns', this.columnForm);
          this.allColumns.push(created);
          this.allColumns.sort((a, b) => a.display_order - b.display_order);
        }
        this.activeColumns = this.allColumns.filter(c => c.is_active);
        this.closeColumnModal();
      } catch (e) {
        this.columnFormError = e.message;
      } finally {
        this.columnFormLoading = false;
      }
    },

    async deleteColumn(col) {
      if (!confirm(`Delete column "${col.field_label}"? This cannot be undone.`)) return;
      try {
        await this.del(`/api/columns/${col.id}`);
        this.allColumns = this.allColumns.filter(c => c.id !== col.id);
        this.activeColumns = this.allColumns.filter(c => c.is_active);
      } catch (e) { alert('Could not delete: ' + e.message); }
    },


    // ── Upload ────────────────────────────────────────────────────
    handleFileSelect(e) {
      const files = Array.from(e.target.files);
      this.uploadFiles = [...this.uploadFiles, ...files];
    },

    handleDrop(e) {
      this.isDragging = false;
      const files = Array.from(e.dataTransfer.files);
      this.uploadFiles = [...this.uploadFiles, ...files];
    },

    async submitUpload() {
      if (!this.uploadFiles.length) return;
      this.uploadLoading = true;
      this.uploadError = '';
      const formData = new FormData();
      this.uploadFiles.forEach(f => formData.append('files', f));

      try {
        const res = await fetch('/api/upload', {
          method: 'POST',
          headers: { Authorization: `Bearer ${this.token}` },
          body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');

        this.showUploadModal = false;
        this.uploadFiles = [];

        // Persist last-used draw/claim selections
        if (this.uploadDrawId) localStorage.setItem('lastDrawId', this.uploadDrawId);
        if (this.uploadProvClaimId) localStorage.setItem('lastProvClaimId', this.uploadProvClaimId);
        if (this.uploadFedClaimId) localStorage.setItem('lastFedClaimId', this.uploadFedClaimId);

        // Assign uploaded invoices to selected draw/claim
        const invoiceIds = data.results.filter(r => r.invoice_id).map(r => r.invoice_id);
        if (invoiceIds.length > 0) {
          if (this.uploadDrawId) {
            try { await this.put(`/api/project/draws/${this.uploadDrawId}/invoices`, invoiceIds); } catch(e) { console.warn('Draw assign:', e); }
          }
          if (this.uploadProvClaimId) {
            try {
              const existing = await this.get(`/api/project/claims/${this.uploadProvClaimId}/invoices`);
              const existingIds = existing.map(i => i.id);
              await this.put(`/api/project/claims/${this.uploadProvClaimId}/invoices`, [...existingIds, ...invoiceIds]);
            } catch(e) { console.warn('Prov claim assign:', e); }
          }
          if (this.uploadFedClaimId) {
            try {
              const existing = await this.get(`/api/project/claims/${this.uploadFedClaimId}/invoices`);
              const existingIds = existing.map(i => i.id);
              await this.put(`/api/project/claims/${this.uploadFedClaimId}/invoices`, [...existingIds, ...invoiceIds]);
            } catch(e) { console.warn('Fed claim assign:', e); }
          }
        }

        // Add to processing queue
        data.results.filter(r => r.status === 'queued').forEach(r => {
          this.processingQueue.push({ id: r.invoice_id, filename: r.filename, status: 'processing' });
        });

        // Start SSE listener
        this.startSSE();

        // Refresh table after short delay
        setTimeout(() => { this.loadInvoices(); this.loadStats(); this.loadProjectDashboard(); }, 1500);
      } catch (e) {
        this.uploadError = e.message;
      } finally {
        this.uploadLoading = false;
      }
    },


    // ── SSE processing updates ────────────────────────────────────
    async startSSE() {
      if (this.sseSource) this.sseSource.close();
      // Get a short-lived (60s) SSE-only token instead of exposing the main JWT
      let sseToken = this.token;
      try {
        const r = await this.post('/api/invoices/sse-token', {});
        sseToken = r.sse_token;
      } catch (e) { /* fallback to main token */ }
      const url = `/api/invoices/stream?token=${encodeURIComponent(sseToken)}`;
      const source = new EventSource(url);
      this.sseSource = source;

      source.onmessage = (e) => {
        const updates = JSON.parse(e.data);
        if (updates.done) { source.close(); this.loadInvoices(); this.loadStats(); return; }
        updates.forEach(update => {
          const idx = this.processingQueue.findIndex(q => q.id === update.id);
          if (idx !== -1) {
            this.processingQueue[idx] = { ...this.processingQueue[idx], ...update };
          } else {
            this.processingQueue.push(update);
          }
          if (update.status === 'processed' || update.status === 'error') {
            setTimeout(() => this.loadInvoices(), 500);
            this.loadStats();
          }
        });
      };
      source.onerror = () => source.close();
    },


    // ── Export ────────────────────────────────────────────────────
    async exportData(format) {
      const params = new URLSearchParams();
      if (this.exportDates.start) params.set('start_date', this.exportDates.start);
      if (this.exportDates.end)   params.set('end_date',   this.exportDates.end);
      if (this.filters.vendor)    params.set('vendor',     this.filters.vendor);
      if (this.filters.currency)  params.set('currency',   this.filters.currency);
      if (this.exportMode)        params.set('mode',       this.exportMode);

      try {
        const res = await fetch(`/api/export/${format}?${params}`, { headers: this._headers() });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const ext = format === 'excel' ? 'xlsx' : 'json';
        a.download = `invoices_${this.exportDates.start || 'all'}_${this.exportDates.end || 'all'}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        alert('Export failed: ' + e.message);
      }
    },


    // ── Admin: API key management ─────────────────────────────────
    async loadApiKeys() {
      try { this.adminApiKeys = await this.get('/api/admin/api-keys'); } catch (e) { console.error(e); }
    },

    openApiKeyModal() {
      this.apiKeyForm = { label: '', key_value: '', priority: 100, is_active: true };
      this.apiKeyFormError = '';
      this.showApiKeyModal = true;
    },

    closeApiKeyModal() {
      this.showApiKeyModal = false;
      this.apiKeyFormError = '';
    },

    async saveApiKey() {
      this.apiKeyFormLoading = true;
      this.apiKeyFormError = '';
      try {
        const key = await this.post('/api/admin/api-keys', this.apiKeyForm);
        this.adminApiKeys.push(key);
        this.adminApiKeys.sort((a, b) => a.priority - b.priority || a.id - b.id);
        this.closeApiKeyModal();
      } catch (e) {
        this.apiKeyFormError = e.message;
      } finally {
        this.apiKeyFormLoading = false;
      }
    },

    async toggleApiKey(key) {
      try {
        const res = await this.put(`/api/admin/api-keys/${key.id}/toggle`, {});
        key.is_active = res.is_active;
      } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteApiKey(key) {
      if (!confirm(`Delete API key "${key.label}"? This cannot be undone.`)) return;
      try {
        await this.del(`/api/admin/api-keys/${key.id}`);
        this.adminApiKeys = this.adminApiKeys.filter(k => k.id !== key.id);
      } catch (e) { alert('Error: ' + e.message); }
    },


    // ── Categories ────────────────────────────────────────────────
    async loadCategories() {
      try {
        this.categoryTree = await this.get('/api/categories');
        // Re-sync selections after reload
        if (this.selectedCategory) {
          this.selectedCategory = this.categoryTree.find(c => c.id === this.selectedCategory.id) || null;
        }
        if (this.selectedSubCategory && this.selectedCategory) {
          this.selectedSubCategory = (this.selectedCategory.children || []).find(c => c.id === this.selectedSubCategory.id) || null;
        }
      } catch (e) { console.error(e); }
      this.loadVendorSummary();
    },

    async loadVendorSummary() {
      try {
        const data = await this.get('/api/categories/vendor-summary');
        this.vendorSummary = data.map(v => ({
          ...v,
          assign_category: v.current_category || '',
          assign_sub_category: v.current_sub_category || '',
        }));
      } catch (e) { console.error(e); }
    },

    async reclassifyAll() {
      this.reclassifying = true;
      this.reclassifyResult = null;
      const mappings = this.vendorSummary
        .filter(v => v.assign_category)
        .map(v => ({
          vendor_name: v.vendor_name,
          category: v.assign_category || null,
          sub_category: v.assign_sub_category || null,
        }));
      if (!mappings.length) {
        alert('No category assignments to apply. Select categories for at least one vendor.');
        this.reclassifying = false;
        return;
      }
      try {
        this.reclassifyResult = await this.post('/api/categories/reclassify', mappings);
        this.loadVendorSummary();
      } catch (e) { alert('Re-classify failed: ' + (e.message || e)); console.error(e); }
      this.reclassifying = false;
    },

    get subCategories() {
      return (this.selectedCategory?.children || []).filter(c => c.level === 'sub_category');
    },

    get subDivisions() {
      return (this.selectedCategory?.children || []).filter(c => c.level === 'sub_division');
    },

    selectCategory(cat) {
      this.selectedCategory = cat;
      this.selectedSubCategory = null;
    },

    selectSubCategory(sc) {
      this.selectedSubCategory = sc;
    },

    openAddCategory(level, parent) {
      this.addCategoryLevel = level;
      this.addCategoryParent = parent;
      this.addCategoryName = '';
      this.addCategoryError = '';
      this.showAddCategoryModal = true;
    },

    async submitAddCategory() {
      if (!this.addCategoryName.trim()) return;
      this.addCategoryLoading = true;
      this.addCategoryError = '';
      try {
        await this.post('/api/categories', {
          name: this.addCategoryName.trim(),
          level: this.addCategoryLevel,
          parent_id: this.addCategoryParent?.id || null,
          display_order: 100,
        });
        this.showAddCategoryModal = false;
        await this.loadCategories();
        if (this.addCategoryLevel === 'sub_category' && this.addCategoryParent) {
          this.selectedCategory = this.categoryTree.find(c => c.id === this.addCategoryParent.id) || null;
        } else if (this.addCategoryLevel === 'sub_division' && this.addCategoryParent) {
          this.selectedCategory = this.categoryTree.find(c => c.id === this.addCategoryParent.id) || null;
        }
      } catch (e) {
        this.addCategoryError = e.message;
      } finally {
        this.addCategoryLoading = false;
      }
    },

    async toggleCategoryActive(item) {
      try {
        await this.put(`/api/categories/${item.id}`, { is_active: !item.is_active });
        await this.loadCategories();
      } catch (e) { alert('Error: ' + e.message); }
    },

    async toggleRequiresSubDivision(cat) {
      try {
        await this.put(`/api/categories/${cat.id}`, { requires_sub_division: !cat.requires_sub_division });
        await this.loadCategories();
        this.selectedCategory = this.categoryTree.find(c => c.id === cat.id) || null;
      } catch (e) { alert('Error: ' + e.message); }
    },

    async deleteCategoryItem(item) {
      const hasChildren = item.children?.length > 0;
      const msg = hasChildren
        ? `Delete "${item.name}" and ALL its children? This cannot be undone.`
        : `Delete "${item.name}"?`;
      if (!confirm(msg)) return;
      try {
        await this.del(`/api/categories/${item.id}`);
        if (this.selectedCategory?.id === item.id) { this.selectedCategory = null; this.selectedSubCategory = null; }
        if (this.selectedSubCategory?.id === item.id) this.selectedSubCategory = null;
        await this.loadCategories();
      } catch (e) { alert('Error: ' + e.message); }
    },


    // ── Project Finance ──────────────────────────────────────────
    async loadProjectDashboard() {
      try {
        this.projectDash = await this.get(`/api/project/dashboard${this._pid}`);
        this.costCategories = this.projectDash?.categories || [];
        this.draws = this.projectDash?.draws || [];
        this.claims = [...(this.projectDash?.provincial_claims || []), ...(this.projectDash?.federal_claims || [])];
        this.loadFinanceInvoices();
      } catch (e) { console.error(e); }
    },

    async loadFinanceInvoices() {
      try {
        let params = 'page=1&limit=500';
        if (this.financeInvoiceFilter === 'unallocated') params += '&unallocated=true';
        else if (this.financeInvoiceFilter === 'no_draw') params += '&draw_id=none';
        else if (this.financeInvoiceFilter === 'no_claim') params += '&claim_id=none';
        const data = await this.get(`/api/invoices?${params}&status=processed`);
        const invs = data.items || [];
        // Enrich with allocation info
        for (const inv of invs) {
          try { inv.allocations = await this.get(`/api/project/allocations/${inv.id}`); } catch (e) { inv.allocations = []; }
        }
        this.financeInvoices = invs;
      } catch (e) { console.error(e); }
    },

    async loadSubdivisions() {
      try { this.subdivisions = await this.get(`/api/project/subdivisions${this._pid}`); } catch (e) {}
    },

    async loadCostCategories() {
      try { this.costCategories = await this.get(`/api/project/categories${this._pid}`); } catch (e) {}
    },

    async updateProjectBudget(field, value) {
      try { await this.put('/api/project', { [field]: value }); await this.loadProjectDashboard(); } catch (e) { alert(e.message); }
    },

    async updateCategoryBudget(catId, budget) {
      try { await this.put(`/api/project/categories/${catId}`, { budget: parseFloat(budget) }); await this.loadProjectDashboard(); } catch (e) { alert(e.message); }
    },

    async updateCategoryLenderBudget(catId, lenderBudget) {
      const val = lenderBudget === '' || lenderBudget == null ? null : parseFloat(lenderBudget);
      try { await this.put(`/api/project/categories/${catId}`, { lender_budget: val }); await this.loadProjectDashboard(); } catch (e) { alert(e.message); }
    },

    // Allocation modal
    async openAllocModal(inv) {
      this.selectedAllocInvoice = inv;
      this.allocations = await this.get(`/api/project/allocations/${inv.id}`);
      if (this.costCategories.length === 0) await this.loadCostCategories();
      if (this.subdivisions.length === 0) await this.loadSubdivisions();
      this.allocForm = { category_id: '', sub_category_id: '', subdivision_id: '', percentage: 100 };
      this.showAllocModal = true;
    },

    allocFormSubCategories() {
      const cat = this.costCategories.find(c => c.id == this.allocForm.category_id);
      return cat?.sub_categories || [];
    },

    allocFormNeedsSubdivision() {
      const cat = this.costCategories.find(c => c.id == this.allocForm.category_id);
      return cat?.is_per_subdivision || false;
    },

    async addAllocation() {
      if (!this.allocForm.category_id) return;
      const remaining = 100 - this.allocations.reduce((s, a) => s + a.percentage, 0);
      const pct = Math.min(parseFloat(this.allocForm.percentage) || 0, remaining);
      if (pct <= 0) { alert('No remaining percentage to allocate'); return; }

      this.allocations.push({
        id: null,
        invoice_id: this.selectedAllocInvoice.id,
        category_id: parseInt(this.allocForm.category_id),
        sub_category_id: this.allocForm.sub_category_id ? parseInt(this.allocForm.sub_category_id) : null,
        subdivision_id: this.allocForm.subdivision_id ? parseInt(this.allocForm.subdivision_id) : null,
        percentage: pct,
        amount: ((this.selectedAllocInvoice.total_due || 0) * pct / 100),
        category_name: this.costCategories.find(c => c.id == this.allocForm.category_id)?.name,
        sub_category_name: null,
        subdivision_name: this.subdivisions.find(s => s.id == this.allocForm.subdivision_id)?.name,
      });
      this.allocForm = { category_id: '', sub_category_id: '', subdivision_id: '', percentage: remaining - pct };
    },

    removeAllocation(idx) {
      this.allocations.splice(idx, 1);
    },

    async saveAllocations() {
      const total = this.allocations.reduce((s, a) => s + a.percentage, 0);
      if (this.allocations.length > 0 && Math.abs(total - 100) > 0.01) {
        alert(`Percentages must total 100% (currently ${total.toFixed(1)}%)`);
        return;
      }
      try {
        await this.put(`/api/project/allocations/${this.selectedAllocInvoice.id}`, this.allocations.map(a => ({
          invoice_id: a.invoice_id,
          category_id: a.category_id,
          sub_category_id: a.sub_category_id,
          subdivision_id: a.subdivision_id,
          percentage: a.percentage,
        })));
        this.showAllocModal = false;
        await this.loadProjectDashboard();
      } catch (e) { alert(e.message); }
    },

    // Payment modal
    async openPaymentModal(inv) {
      this.paymentForm = { invoice_id: inv.id, amount: '', payment_date: new Date().toISOString().slice(0, 10), method: '', reference: '', notes: '' };
      this.invoicePayments = await this.get(`/api/project/payments/${inv.id}`);
      this.showPaymentModal = true;
    },

    async submitPayment() {
      if (!this.paymentForm.amount || !this.paymentForm.payment_date) return;
      try {
        await this.post('/api/project/payments', {
          ...this.paymentForm,
          amount: parseFloat(this.paymentForm.amount),
        });
        this.invoicePayments = await this.get(`/api/project/payments/${this.paymentForm.invoice_id}`);
        this.paymentForm.amount = '';
        this.paymentForm.reference = '';
        this.paymentForm.notes = '';
        await Promise.all([this.loadInvoices(), this.loadProjectDashboard()]);
      } catch (e) { alert(e.message); }
    },

    async deletePayment(pmtId, invoiceId) {
      if (!confirm('Delete this payment?')) return;
      try {
        await this.del(`/api/project/payments/${pmtId}`);
        this.invoicePayments = await this.get(`/api/project/payments/${invoiceId}`);
        await Promise.all([this.loadInvoices(), this.loadProjectDashboard()]);
      } catch (e) { alert(e.message); }
    },

    paymentBadge(status) {
      return {
        'paid':           'bg-green-100 text-green-700',
        'partially_paid': 'bg-amber-100 text-amber-700',
        'unpaid':         'bg-red-100 text-red-600',
      }[status] || 'bg-gray-100 text-gray-600';
    },

    async exportBookkeeping() {
      try {
        const res = await fetch('/api/project/export/bookkeeping', { headers: this._headers() });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bookkeeping_${new Date().toISOString().slice(0, 10)}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) { alert('Export failed: ' + e.message); }
    },

    budgetHealth(remaining, budget) {
      if (!budget || budget <= 0) return 'text-gray-400';
      const pct = remaining / budget;
      if (pct > 0.2) return 'text-green-600';
      if (pct > 0) return 'text-amber-500';
      return 'text-red-600';
    },

    // ── Draws ──────────────────────────────────────────────────────
    async loadDraws() {
      try { this.draws = await this.get(`/api/project/draws${this._pid}`); } catch (e) {}
    },

    openDrawModal(draw = null) {
      if (draw) {
        this.editingDrawId = draw.id;
        this.drawForm = { draw_number: draw.draw_number, fx_rate: draw.fx_rate, submission_date: draw.submission_date || '', status: draw.status, notes: draw.notes || '' };
      } else {
        this.editingDrawId = null;
        const next = this.draws.length ? Math.max(...this.draws.map(d => d.draw_number)) + 1 : 1;
        this.drawForm = { draw_number: next, fx_rate: 1.0, submission_date: '', status: 'draft', notes: '' };
      }
      this.drawFormError = '';
      this.showDrawModal = true;
    },

    async fetchFxRate(target) {
      this.fxRateLoading = true;
      try {
        const date = (target === 'draw' ? this.drawForm.submission_date : this.claimForm.submission_date) || '';
        const r = await this.get('/api/project/fx-rate' + (date ? '?date=' + date : ''));
        if (target === 'draw') this.drawForm.fx_rate = r.rate;
        else this.claimForm.fx_rate = r.rate;
      } catch (e) { alert('Could not fetch rate'); }
      this.fxRateLoading = false;
    },

    async saveDraw() {
      try {
        if (this.editingDrawId) {
          await this.put(`/api/project/draws/${this.editingDrawId}`, { fx_rate: this.drawForm.fx_rate, submission_date: this.drawForm.submission_date || null, status: this.drawForm.status, notes: this.drawForm.notes || null });
        } else {
          await this.post(`/api/project/draws${this._pid}`, this.drawForm);
        }
        this.showDrawModal = false;
        await Promise.all([this.loadDraws(), this.loadProjectDashboard()]);
      } catch (e) { this.drawFormError = e.message; }
    },

    async deleteDraw(drawId) {
      if (!confirm('Delete this draw and unlink all its invoices?')) return;
      try {
        await this.del(`/api/project/draws/${drawId}`);
        await Promise.all([this.loadDraws(), this.loadProjectDashboard()]);
      } catch (e) { alert(e.message); }
    },

    // ── Claims ─────────────────────────────────────────────────────
    async loadClaims() {
      try { this.claims = await this.get(`/api/project/claims${this._pid}`); } catch (e) {}
    },

    openClaimModal(claim = null, claimType = 'provincial') {
      if (claim) {
        this.editingClaimId = claim.id;
        this.claimForm = { claim_number: claim.claim_number, claim_type: claim.claim_type, fx_rate: claim.fx_rate, submission_date: claim.submission_date || '', status: claim.status, notes: claim.notes || '' };
      } else {
        this.editingClaimId = null;
        const existing = this.claims.filter(c => c.claim_type === claimType);
        const next = existing.length ? Math.max(...existing.map(c => c.claim_number)) + 1 : 1;
        this.claimForm = { claim_number: next, claim_type: claimType, fx_rate: 1.0, submission_date: '', status: 'draft', notes: '' };
      }
      this.claimFormError = '';
      this.showClaimModal = true;
    },

    async saveClaim() {
      try {
        if (this.editingClaimId) {
          await this.put(`/api/project/claims/${this.editingClaimId}`, { fx_rate: this.claimForm.fx_rate, submission_date: this.claimForm.submission_date || null, status: this.claimForm.status, notes: this.claimForm.notes || null });
        } else {
          await this.post(`/api/project/claims${this._pid}`, this.claimForm);
        }
        this.showClaimModal = false;
        await Promise.all([this.loadClaims(), this.loadProjectDashboard()]);
      } catch (e) { this.claimFormError = e.message; }
    },

    async deleteClaim(claimId) {
      if (!confirm('Delete this claim and unlink all its invoices?')) return;
      try {
        await this.del(`/api/project/claims/${claimId}`);
        await Promise.all([this.loadClaims(), this.loadProjectDashboard()]);
      } catch (e) { alert(e.message); }
    },

    async copyDrawToClaim(claimId, drawId) {
      try {
        await this.put(`/api/project/claims/${claimId}/copy-from-draw/${drawId}`, {});
        await Promise.all([this.loadClaims(), this.loadProjectDashboard()]);
        alert('Invoices copied from draw to claim');
      } catch (e) { alert(e.message); }
    },

    // ── Assign Invoices Modal ──────────────────────────────────────
    async openAssignInvoices(type, id, number) {
      this.assignTarget = { type, id, number };
      // Load all processed invoices
      const allInvs = (await this.get('/api/invoices?limit=1000')).items || [];
      this.assignableInvoices = allInvs.filter(i => i.status === 'processed');
      // Load currently assigned
      const endpoint = type === 'draw' ? `/api/project/draws/${id}/invoices` : `/api/project/claims/${id}/invoices`;
      const assigned = await this.get(endpoint);
      this.assignedInvoiceIds = assigned.map(i => i.id);
      this.showAssignInvoicesModal = true;
    },

    toggleAssignInvoice(invId) {
      const idx = this.assignedInvoiceIds.indexOf(invId);
      if (idx >= 0) this.assignedInvoiceIds.splice(idx, 1);
      else this.assignedInvoiceIds.push(invId);
    },

    async saveAssignedInvoices() {
      const t = this.assignTarget;
      const endpoint = t.type === 'draw' ? `/api/project/draws/${t.id}/invoices` : `/api/project/claims/${t.id}/invoices`;
      try {
        await this.put(endpoint, this.assignedInvoiceIds);
        this.showAssignInvoicesModal = false;
        await Promise.all([this.loadDraws(), this.loadClaims(), this.loadProjectDashboard(), this.loadInvoices()]);
      } catch (e) { alert(e.message); }
    },

    statusColor(status) {
      return { draft: 'bg-gray-100 text-gray-700', submitted: 'bg-blue-100 text-blue-700', approved: 'bg-green-100 text-green-700', funded: 'bg-emerald-100 text-emerald-800', received: 'bg-emerald-100 text-emerald-800' }[status] || 'bg-gray-100 text-gray-600';
    },

    // ── Payroll ──────────────────────────────────────────────────
    async loadPayroll() {
      try { this.payrollEntries = await this.get(`/api/project/payroll${this._pid}`); } catch(e) { this.payrollEntries = []; }
    },
    openPayrollModal(entry = null) {
      if (entry) {
        this.editingPayrollId = entry.id;
        this.payrollForm = { ...entry };
      } else {
        this.editingPayrollId = null;
        this.payrollForm = { employee_name: '', company_name: '', pay_period_start: '', pay_period_end: '', gross_pay: 0, cpp: 0, ei: 0, income_tax: 0, insurance: 0, holiday_pay: 0, other_deductions: 0, working_days: 22, statutory_holidays: 0, province: 'ON' };
      }
      this.payrollFormError = '';
      this.showPayrollModal = true;
    },
    async savePayroll() {
      try {
        if (this.editingPayrollId) {
          await this.put(`/api/project/payroll/${this.editingPayrollId}`, this.payrollForm);
        } else {
          await this.post(`/api/project/payroll${this._pid}`, this.payrollForm);
        }
        this.showPayrollModal = false;
        await Promise.all([this.loadPayroll(), this.loadProjectDashboard()]);
      } catch(e) { this.payrollFormError = e.message; }
    },
    async deletePayroll(id) {
      if (!confirm('Delete this payroll entry?')) return;
      await this.del(`/api/project/payroll/${id}`);
      await Promise.all([this.loadPayroll(), this.loadProjectDashboard()]);
    },

    // ── Quick Create Draw/Claim from Upload Modal ──────────────
    async quickCreateDraw() {
      const num = prompt('Enter draw number:');
      if (!num) return;
      const rate = prompt('USD→CAD FX rate (default 1.0):', '1.0');
      try {
        const res = await this.post(`/api/project/draws${this._pid}`, { draw_number: parseInt(num), fx_rate: parseFloat(rate) || 1.0 });
        await this.loadDraws();
        this.uploadDrawId = res.id;
      } catch(e) { alert(e.message); }
    },
    async quickCreateClaim(type) {
      const num = prompt(`Enter ${type} claim number:`);
      if (!num) return;
      const rate = prompt('USD→CAD FX rate (default 1.0):', '1.0');
      try {
        const res = await this.post(`/api/project/claims${this._pid}`, { claim_number: parseInt(num), claim_type: type, fx_rate: parseFloat(rate) || 1.0 });
        await this.loadClaims();
        if (type === 'provincial') this.uploadProvClaimId = res.id;
        else this.uploadFedClaimId = res.id;
      } catch(e) { alert(e.message); }
    },

    // ── Bulk Approve ────────────────────────────────────────────
    async bulkApproveDraw(drawId) {
      if (!confirm('Approve ALL invoices in this draw? You can adjust individual ones after.')) return;
      try {
        const res = await this.post(`/api/project/draws/${drawId}/approve-all`, {});
        alert(`${res.count} invoices approved`);
        await Promise.all([this.loadDraws(), this.loadProjectDashboard(), this.loadInvoices()]);
      } catch(e) { alert(e.message); }
    },
    async bulkApproveClaim(claimId) {
      if (!confirm('Approve ALL invoices in this claim? You can adjust individual ones after.')) return;
      try {
        const res = await this.post(`/api/project/claims/${claimId}/approve-all`, {});
        alert(`${res.count} invoices approved`);
        await Promise.all([this.loadClaims(), this.loadProjectDashboard(), this.loadInvoices()]);
      } catch(e) { alert(e.message); }
    },

    // ── Invoice Cost Update ─────────────────────────────────────
    async updateInvoiceCost(invId, field, value) {
      try {
        await this.put(`/api/project/invoices/${invId}/cost`, { [field]: value });
        await this.loadInvoices();
      } catch(e) { alert(e.message); }
    },

    // ── Settings ──────────────────────────────────────────────────
    async saveSettings() {
      this.settingsSaved = true;
      setTimeout(() => this.settingsSaved = false, 5000);
    },

    // ── User Management (admin) ─────────────────────────────────
    adminUsers: [],
    showCreateUserModal: false,
    retryingInvoices: false,
    createUserForm: { username: '', email: '', password: '', is_admin: false, org_role: 'editor' },
    createUserError: '',
    changePwForm: { current_password: '', new_password: '' },
    changePwMsg: '',
    changePwError: false,

    async loadUsers() {
      if (!this.user?.is_admin) return;
      try { this.adminUsers = await this.get('/api/admin/users'); } catch(e) { this.adminUsers = []; }
    },
    async createUser() {
      this.createUserError = '';
      try {
        // Username = email (same field)
        this.createUserForm.username = this.createUserForm.email;
        const newUser = await this.post('/api/admin/users', this.createUserForm);
        // Optionally add to current org with selected role
        if (this.createUserForm.org_role && this.currentOrg) {
          try {
            await this.post('/api/org/members', {
              username: newUser.username,
              role: this.createUserForm.org_role,
            });
          } catch(e) { /* user created, org add failed — not fatal */ }
        }
        this.showCreateUserModal = false;
        this.createUserForm = { username: '', email: '', password: '', is_admin: false, org_role: 'editor' };
        await this.loadUsers();
        await this.loadOrgMembers();
      } catch(e) { this.createUserError = e.message; }
    },
    async toggleUserActive(u) {
      try {
        const res = await this.put(`/api/admin/users/${u.id}/toggle-active`, {});
        u.is_active = res.is_active;
      } catch(e) { alert(e.message); }
    },
    async resetUserPassword(u) {
      const pw = prompt(`Enter new password for ${u.username} (min 8 chars):`);
      if (!pw) return;
      try {
        await this.put(`/api/admin/users/${u.id}/reset-password`, { password: pw });
        alert(`Password reset for ${u.username}`);
      } catch(e) { alert(e.message); }
    },
    async deleteUser(u) {
      if (!confirm(`Delete user "${u.username}"? This cannot be undone.`)) return;
      try {
        await this.del(`/api/admin/users/${u.id}`);
        await this.loadUsers();
      } catch(e) { alert(e.message); }
    },
    async changePassword() {
      this.changePwMsg = '';
      this.changePwError = false;
      try {
        await this.put('/api/auth/change-password', this.changePwForm);
        this.changePwMsg = 'Password changed successfully';
        this.changePwForm = { current_password: '', new_password: '' };
      } catch(e) {
        this.changePwMsg = e.message;
        this.changePwError = true;
      }
    },


    // ── Helpers ───────────────────────────────────────────────────
    getCellValue(inv, col) {
      if (!inv) return '';
      const data = inv.extracted_data || {};
      let val = data[col.field_key];
      if (val === undefined || val === null) {
        val = inv[col.field_key];
      }
      if (val === null || val === undefined) return '';
      if (Array.isArray(val)) return `[${val.length} items]`;
      if (col.field_type === 'number' && typeof val === 'number') return this.fmtNum(val);
      return String(val);
    },

    fmtNum(val) {
      if (val === null || val === undefined || val === '') return '';
      const n = parseFloat(val);
      if (isNaN(n)) return val;
      return n.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },

    formatBytes(bytes) {
      if (bytes < 1024) return bytes + ' B';
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
      return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    },

    statusBadge(status) {
      return {
        'processed':  'bg-green-100 text-green-700',
        'processing': 'bg-amber-100 text-amber-700',
        'pending':    'bg-gray-100 text-gray-600',
        'error':      'bg-red-100 text-red-600',
      }[status] || 'bg-gray-100 text-gray-600';
    },


    // ── File Tools ──────────────────────────────────────────────
    async handleFinderCsv(event) {
      const file = event.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      try {
        const r = await fetch('/api/filetools/upload-csv', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${this.token}` },
          body: formData,
        });
        if (!r.ok) { const e = await r.json(); alert(e.detail || 'Parse error'); return; }
        const data = await r.json();
        this.finderInvoices = data.invoices || [];
      } catch (e) { alert('Failed to parse file'); console.error(e); }
    },

    async runInvoiceFinder(mode = 'fast') {
      this.finderSearching = true;
      const prevResults = mode === 'deep' ? { ...this.finderResults } : null;
      if (mode === 'fast') this.finderResults = { total: 0, searched: 0, found: 0, duplicates: 0, missing: 0, found_list: [], duplicate_list: [], missing_list: [] };
      localStorage.setItem('finderSourceFolder', this.finderSourceFolder);

      const invoicesToSearch = mode === 'deep' && prevResults?.missing_list
        ? prevResults.missing_list.map(m => ({ vendor: m.vendor, invoice_number: m.invoice_number }))
        : this.finderInvoices;

      try {
        const resp = await fetch('/api/filetools/find-invoices', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${this.token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_folder: this.finderSourceFolder,
            output_folder: this.finderOutputFolder || null,
            invoices: invoicesToSearch,
            mode: mode,
          }),
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === 'progress') {
                // Update live counters
                if (mode === 'deep' && prevResults) {
                  this.finderResults = {
                    ...this.finderResults,
                    searched: event.searched,
                    total: event.total,
                    found: (prevResults.found || 0) + event.found,
                    duplicates: (prevResults.duplicates || 0) + event.duplicates,
                    missing: event.missing,
                    vendor: event.vendor,
                    invoice_number: event.invoice_number,
                    deepMode: true,
                  };
                } else {
                  this.finderResults = { ...this.finderResults, ...event };
                }
              } else if (event.type === 'done') {
                if (mode === 'deep' && prevResults) {
                  this.finderResults = {
                    ...this.finderResults,
                    cancelled: event.cancelled,
                    found: (prevResults.found || 0) + event.found,
                    duplicates: (prevResults.duplicates || 0) + event.duplicates,
                    missing: event.missing,
                    found_list: [...(prevResults.found_list || []), ...event.found_list],
                    duplicate_list: [...(prevResults.duplicate_list || []), ...event.duplicate_list],
                    missing_list: event.missing_list,
                    output_folder: event.output_folder,
                  };
                } else {
                  this.finderResults = event;
                }
              }
            } catch (e) {}
          }
        }
      } catch (e) { alert('Search failed: ' + (e.message || e)); console.error(e); }
      this.finderSearching = false;
    },

    async cancelSearch() {
      try { await this.post('/api/filetools/find-invoices/cancel', {}); } catch (e) {}
    },

    exportMissingCsv() {
      const missing = this.finderResults?.missing_list || [];
      if (!missing.length) return;
      let csv = 'Vendor,Invoice Number,Reason\n';
      for (const m of missing) {
        csv += `"${(m.vendor||'').replace(/"/g,'""')}","${(m.invoice_number||'').replace(/"/g,'""')}","${(m.reason||'').replace(/"/g,'""')}"\n`;
      }
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `missing_invoices_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    },

    async runBulkUpload() {
      this.bulkUploading = true;
      this.bulkResults = null;
      localStorage.setItem('bulkFolderPath', this.bulkFolderPath);
      try {
        this.bulkResults = await this.post(`/api/filetools/bulk-upload-folder?folder_path=${encodeURIComponent(this.bulkFolderPath)}`, {});
        // Refresh dashboard after upload
        setTimeout(() => { this.loadInvoices(); this.loadStats(); this.loadProjectDashboard(); }, 2000);
      } catch (e) { alert('Upload failed: ' + (e.message || e)); console.error(e); }
      this.bulkUploading = false;
    },

    // ── HTTP helpers ─────────────────────────────────────────────
    async get(path) {
      const res = await fetch(API + path, { headers: this._headers() });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
      }
      return res.json();
    },

    async post(path, body, auth = true) {
      const res = await fetch(API + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(auth ? this._headers() : {}) },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
      }
      return res.json();
    },

    async put(path, body) {
      const res = await fetch(API + path, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...this._headers() },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
      }
      return res.json();
    },

    async del(path) {
      const res = await fetch(API + path, { method: 'DELETE', headers: this._headers() });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
      }
      return res.json();
    },

    _headers() {
      const h = this.token ? { Authorization: `Bearer ${this.token}` } : {};
      if (this.currentOrg?.id) h['X-Organization-Id'] = String(this.currentOrg.id);
      return h;
    },

    // ── Funding Conditions functions ──────────────────────────────
    async loadConditions(drawId) {
      this.activeDrawForConditions = drawId;
      try { this.drawConditions = await this.get(`/api/project/draws/${drawId}/conditions`); }
      catch(e) { this.drawConditions = []; }
    },
    async saveCondition(drawId) {
      await this.post(`/api/project/draws/${drawId}/conditions`, this.conditionForm);
      this.showConditionModal = false;
      this.conditionForm = { description:'', condition_type:'document', required_by:'' };
      await this.loadConditions(drawId);
    },
    async satisfyCondition(id, drawId) {
      await this.put(`/api/project/conditions/${id}`, { status:'satisfied' });
      await this.loadConditions(drawId);
    },
    async loadCertificates(drawId) {
      this.activeDrawForCerts = drawId;
      try { this.drawCertificates = await this.get(`/api/project/draws/${drawId}/certificates`); }
      catch(e) { this.drawCertificates = []; }
    },
    async saveCertificate(drawId) {
      await this.post(`/api/project/draws/${drawId}/certificates`, this.certForm);
      this.showCertModal = false;
      this.certForm = { cert_type:'progress', certifier_name:'', certifier_firm:'', cert_date:'', amount_certified:'' };
      await this.loadCertificates(drawId);
    },
    openCCDCClaim(drawId) { window.open(`/api/project/draws/${drawId}/ccdc-claim`, '_blank'); },
    conditionStatusColor(s) {
      return { open:'bg-amber-100 text-amber-700', satisfied:'bg-green-100 text-green-700', waived:'bg-gray-100 text-gray-500', submitted:'bg-blue-100 text-blue-700' }[s] || 'bg-gray-100';
    },

    // ── Owner Tokens functions ────────────────────────────────────
    async loadOwnerTokens() {
      try { this.ownerTokens = await this.get('/api/project/owner-tokens'); }
      catch(e) { this.ownerTokens = []; }
    },
    async createOwnerToken() {
      if (!this.currentProject) return;
      const body = { ...this.ownerTokenForm, project_id: this.currentProject.id };
      await this.post('/api/project/owner-tokens', body);
      this.showOwnerTokenModal = false;
      this.ownerTokenForm = { label:'', expires_at:'' };
      await this.loadOwnerTokens();
    },
    async toggleOwnerToken(id) {
      await fetch(`/api/project/owner-tokens/${id}/toggle`, { method:'PUT', headers: this._headers() });
      await this.loadOwnerTokens();
    },
    async deleteOwnerToken(id) {
      if (!confirm('Delete this owner portal link?')) return;
      await this.delete(`/api/project/owner-tokens/${id}`);
      await this.loadOwnerTokens();
    },

    // ── Canadian Compliance ───────────────────────────────────────
    async loadVendorCompliance() {
      this.vendorComplianceLoading = true;
      try { this.vendorCompliance = await this.get('/api/compliance/vendors'); }
      catch(e) { this.vendorCompliance = null; }
      finally { this.vendorComplianceLoading = false; }
    },
    openVendorComplianceModal(v) {
      this.selectedVendorCompliance = v;
      this.vendorComplianceForm = {
        wsib_number: v.wsib_number||'', wsib_expiry: v.wsib_expiry||'',
        wcb_number: v.wcb_number||'', wcb_expiry: v.wcb_expiry||'',
        insurance_expiry: v.insurance_expiry||'',
        liability_limit: v.liability_limit||'',
        cra_business_number: v.cra_business_number||'',
        province: v.province||'ON',
        is_incorporated: v.is_incorporated||false,
        statutory_declaration_date: v.statutory_declaration_date||'',
      };
      this.showVendorComplianceModal = true;
    },
    async saveVendorCompliance() {
      await this.put('/api/compliance/vendors/'+this.selectedVendorCompliance.id+'/compliance', this.vendorComplianceForm);
      this.showVendorComplianceModal = false;
      await this.loadVendorCompliance();
    },
    async loadT5018() {
      this.t5018Loading = true;
      try { this.t5018Data = await this.get('/api/compliance/t5018?year='+this.t5018Year); }
      catch(e) { this.t5018Data = null; }
      finally { this.t5018Loading = false; }
    },
    downloadT5018CSV() {
      window.open('/api/compliance/t5018?year='+this.t5018Year+'&format=csv', '_blank');
    },
    complianceSeverityClass(s) {
      return { critical:'border-red-200 bg-red-50', warning:'border-amber-200 bg-amber-50', ok:'border-gray-100 bg-white' }[s]||'bg-white';
    },

    // ── Cost-to-Complete ──────────────────────────────────────────
    async loadCostToComplete() {
      if (!this.currentProject) return;
      this.ctcLoading = true;
      try { this.ctcData = await this.get('/api/compliance/cost-to-complete?project_id='+this.currentProject.id); }
      catch(e) { this.ctcData = null; }
      finally { this.ctcLoading = false; }
    },
    velocityClass(r) {
      return { on_track:'text-green-600', over_budget:'text-amber-600', critical:'text-red-600' }[r]||'text-gray-600';
    },
    eacVarianceClass(v) { return v >= 0 ? 'text-green-600' : 'text-red-600'; },
    downloadQBExport() {
      const params = new URLSearchParams();
      if (this.currentProject) params.set('project_id', this.currentProject.id);
      window.open('/api/compliance/export/quickbooks?'+params, '_blank');
    },
    downloadXeroExport() {
      const params = new URLSearchParams();
      if (this.currentProject) params.set('project_id', this.currentProject.id);
      window.open('/api/compliance/export/xero?'+params, '_blank');
    },

    // ── Pay Readiness ─────────────────────────────────────────────
    async loadPayReadiness() {
      if (!this.currentProject) return;
      this.payReadinessLoading = true;
      try { this.payReadiness = await this.get('/api/compliance/vendor-pay-readiness?project_id='+this.currentProject.id); }
      catch(e) { this.payReadiness = null; }
      finally { this.payReadinessLoading = false; }
    },
    stageColor(s) {
      return { blocked:'bg-red-100 text-red-700', received:'bg-gray-100 text-gray-600',
               submitted_to_lender:'bg-blue-100 text-blue-700', approved:'bg-amber-100 text-amber-700',
               ready_to_pay:'bg-green-100 text-green-700', paid:'bg-slate-100 text-slate-500' }[s]||'bg-gray-100';
    },
    stageLabel(s) {
      return { blocked:'Blocked', received:'Received', submitted_to_lender:'With Lender',
               approved:'Approved', ready_to_pay:'Ready to Pay', paid:'Paid' }[s]||s;
    },

    // ── Contract Matching ─────────────────────────────────────────
    async loadContractMatching() {
      if (!this.currentProject) return;
      this.contractMatchingLoading = true;
      try { this.contractMatching = await this.get('/api/compliance/contract-matching?project_id='+this.currentProject.id); }
      catch(e) { this.contractMatching = null; }
      finally { this.contractMatchingLoading = false; }
    },
    matchConfidenceColor(c) {
      if (c >= 0.9) return 'text-green-600'; if (c >= 0.7) return 'text-amber-600'; return 'text-red-500';
    },

    // ── AI Construction Accountant ────────────────────────────────
    async loadHealthCheck() {
      if (!this.currentProject) return;
      this.healthLoading = true;
      try {
        this.healthData = await this.get(
          `/api/project/ai/construction-health?project_id=${this.currentProject.id}`
        );
      } catch(e) { this.healthData = null; }
      finally { this.healthLoading = false; }
    },
    healthSeverityClass(s) {
      return { critical:'bg-red-100 text-red-700 border-red-200',
               warning:'bg-amber-50 text-amber-700 border-amber-200',
               info:'bg-blue-50 text-blue-700 border-blue-200' }[s] || 'bg-gray-50 text-gray-600 border-gray-200';
    },
    healthIconClass(s) {
      return { critical:'fa-circle-xmark text-red-500',
               warning:'fa-triangle-exclamation text-amber-500',
               info:'fa-circle-info text-blue-400' }[s] || 'fa-circle-info text-gray-400';
    },
    scoreColor(score) {
      if (score >= 90) return 'text-green-600';
      if (score >= 75) return 'text-blue-600';
      if (score >= 55) return 'text-amber-600';
      return 'text-red-600';
    },
    openDrawPackage(drawId) {
      window.open(`/api/project/draws/${drawId}/package`, '_blank');
    },

    // ── Cash Flow ─────────────────────────────────────────────────
    async loadCashFlowData() {
      if (!this.currentProject) return;
      this.cashFlowLoading = true;
      try {
        this.cashFlowData = await this.get('/api/project/cash-flow');
      } catch(e) { this.cashFlowData = null; }
      finally { this.cashFlowLoading = false; }
    },
    cfBarHeight(val, max) {
      if (!max || max === 0) return '2px';
      return Math.max(4, Math.round(Math.abs(val) / max * 100)) + 'px';
    },

    // ── PM helpers ────────────────────────────────────────────────
    get canAccessPM() {
      const pm = ['owner','admin','pm_admin','pm_viewer','site_supervisor','vendor_pm','editor','viewer'];
      return pm.includes(this.currentOrg?.role);
    },
    get canAccessFinance() {
      const f = ['owner','admin','finance_admin','finance_viewer','site_supervisor','editor','viewer'];
      return f.includes(this.currentOrg?.role);
    },
    get isVendorFinance() { return this.currentOrg?.role === 'vendor_finance'; },
    get isVendorPM()      { return this.currentOrg?.role === 'vendor_pm'; },
    get canWritePM() {
      return ['owner','admin','pm_admin','site_supervisor','editor','vendor_pm'].includes(this.currentOrg?.role);
    },

    _pmParams(extra = {}) {
      const p = new URLSearchParams({ project_id: this.currentProject?.id || '', ...extra });
      return p.toString();
    },

    async loadPMSummary() {
      if (!this.currentProject) return;
      try { this.pmSummary = await this.get('/api/pm/summary?' + this._pmParams()); } catch(e) {}
    },

    // Tasks
    async loadPMTasks() {
      if (!this.currentProject) return;
      this.pmTasksLoading = true;
      try {
        const p = { project_id: this.currentProject.id };
        if (this.pmTaskFilter.status) p.status = this.pmTaskFilter.status;
        if (this.pmTaskFilter.assigned_to) p.assigned_to = this.pmTaskFilter.assigned_to;
        this.pmTasks = await this.get('/api/pm/tasks?' + new URLSearchParams(p));
      } catch(e) { this.pmTasks = []; }
      finally { this.pmTasksLoading = false; }
    },
    openTaskModal(task = null) {
      this.editingTask = task;
      if (task) {
        this.taskForm = { title: task.title, description: task.description||'',
          task_type: task.task_type, status: task.status, priority: task.priority,
          assigned_to: task.assigned_to, start_date: task.start_date||'',
          end_date: task.end_date||'', due_date: task.due_date||'',
          percent_complete: task.percent_complete, location: task.location||'', tags: task.tags||'' };
      } else {
        this.taskForm = { title:'', description:'', task_type:'task', status:'not_started',
          priority:'medium', assigned_to:null, start_date:'', end_date:'',
          due_date:'', percent_complete:0, location:'', tags:'' };
      }
      this.showTaskModal = true;
    },
    async saveTask() {
      const body = { ...this.taskForm, project_id: this.currentProject?.id };
      try {
        if (this.editingTask) await this.put('/api/pm/tasks/' + this.editingTask.id, body);
        else await this.post('/api/pm/tasks', body);
        this.showTaskModal = false;
        await this.loadPMTasks(); await this.loadPMSummary();
      } catch(e) { alert(e.message); }
    },
    async deleteTask(id) {
      if (!confirm('Delete this task?')) return;
      await this.delete('/api/pm/tasks/' + id);
      await this.loadPMTasks(); await this.loadPMSummary();
    },
    async openTaskDetail(task) {
      this.selectedTask = task;
      this.showTaskDetail = true;
      this.taskCommentsLoading = true;
      try { this.taskComments = await this.get('/api/pm/tasks/' + task.id + '/comments'); }
      catch(e) { this.taskComments = []; }
      finally { this.taskCommentsLoading = false; }
    },
    async postComment() {
      if (!this.newComment.trim()) return;
      await this.post('/api/pm/tasks/' + this.selectedTask.id + '/comments', { comment: this.newComment });
      this.newComment = '';
      this.taskComments = await this.get('/api/pm/tasks/' + this.selectedTask.id + '/comments');
    },
    taskStatusColor(s) {
      return { not_started:'bg-gray-100 text-gray-600', in_progress:'bg-blue-100 text-blue-700',
               completed:'bg-green-100 text-green-700', blocked:'bg-red-100 text-red-700',
               cancelled:'bg-slate-100 text-slate-500' }[s] || 'bg-gray-100 text-gray-600';
    },
    priorityColor(p) {
      return { low:'text-gray-400', medium:'text-amber-500', high:'text-orange-500', critical:'text-red-600' }[p] || 'text-gray-400';
    },

    // Daily Logs
    async loadDailyLogs() {
      if (!this.currentProject) return;
      this.pmDailyLogsLoading = true;
      try { this.pmDailyLogs = await this.get('/api/pm/daily-logs?' + this._pmParams()); }
      catch(e) { this.pmDailyLogs = []; }
      finally { this.pmDailyLogsLoading = false; }
    },
    async saveDailyLog() {
      const body = { ...this.dailyLogForm, project_id: this.currentProject?.id };
      if (!body.log_date) body.log_date = new Date().toISOString().slice(0,10);
      await this.post('/api/pm/daily-logs', body);
      this.showDailyLogModal = false;
      this.dailyLogForm = { log_date:'', weather:'sunny', temperature:'', crew_count:0, work_summary:'', issues:'', delays:'', visitors:'' };
      await this.loadDailyLogs(); await this.loadPMSummary();
    },
    async deleteDailyLog(id) {
      if (!confirm('Delete this log?')) return;
      await this.delete('/api/pm/daily-logs/' + id);
      await this.loadDailyLogs();
    },

    // RFIs
    async loadRFIs() {
      if (!this.currentProject) return;
      this.pmRFIsLoading = true;
      try { this.pmRFIs = await this.get('/api/pm/rfis?' + this._pmParams()); }
      catch(e) { this.pmRFIs = []; }
      finally { this.pmRFIsLoading = false; }
    },
    openRFIModal(rfi = null) {
      this.editingRFI = rfi;
      this.rfiForm = rfi ? { rfi_number: rfi.rfi_number, subject: rfi.subject,
        description: rfi.description||'', priority: rfi.priority,
        assigned_to: rfi.assigned_to, due_date: rfi.due_date||'', response: rfi.response||'' }
        : { rfi_number:'', subject:'', description:'', priority:'medium', assigned_to:null, due_date:'', response:'' };
      this.showRFIModal = true;
    },
    async saveRFI() {
      const body = { ...this.rfiForm, project_id: this.currentProject?.id };
      if (this.editingRFI) await this.put('/api/pm/rfis/' + this.editingRFI.id, body);
      else await this.post('/api/pm/rfis', body);
      this.showRFIModal = false;
      await this.loadRFIs(); await this.loadPMSummary();
    },
    async deleteRFI(id) {
      if (!confirm('Delete this RFI?')) return;
      await this.delete('/api/pm/rfis/' + id);
      await this.loadRFIs();
    },

    // Punch list
    async loadPunchList() {
      if (!this.currentProject) return;
      this.pmPunchLoading = true;
      try { this.pmPunchItems = await this.get('/api/pm/punch-list?' + this._pmParams()); }
      catch(e) { this.pmPunchItems = []; }
      finally { this.pmPunchLoading = false; }
    },
    openPunchModal(item = null) {
      this.editingPunch = item;
      this.punchForm = item ? { title: item.title, description: item.description||'',
        location: item.location||'', priority: item.priority,
        assigned_to: item.assigned_to, due_date: item.due_date||'' }
        : { title:'', description:'', location:'', priority:'medium', assigned_to:null, due_date:'' };
      this.showPunchModal = true;
    },
    async savePunch() {
      const body = { ...this.punchForm, project_id: this.currentProject?.id };
      if (this.editingPunch) await this.put('/api/pm/punch-list/' + this.editingPunch.id, body);
      else await this.post('/api/pm/punch-list', body);
      this.showPunchModal = false;
      await this.loadPunchList(); await this.loadPMSummary();
    },
    async resolvePunch(id) {
      await this.put('/api/pm/punch-list/' + id, { status: 'resolved' });
      await this.loadPunchList();
    },
    async deletePunch(id) {
      if (!confirm('Delete this item?')) return;
      await this.delete('/api/pm/punch-list/' + id);
      await this.loadPunchList();
    },

    // Submittals
    async loadSubmittals() {
      if (!this.currentProject) return;
      this.pmSubmittalsLoading = true;
      try { this.pmSubmittals = await this.get('/api/pm/submittals?' + this._pmParams()); }
      catch(e) { this.pmSubmittals = []; }
      finally { this.pmSubmittalsLoading = false; }
    },
    async saveSubmittal() {
      const body = { ...this.submittalForm, project_id: this.currentProject?.id };
      await this.post('/api/pm/submittals', body);
      this.showSubmittalModal = false;
      this.submittalForm = { title:'', spec_section:'', status:'draft', submitted_date:'', reviewer:null, review_notes:'' };
      await this.loadSubmittals(); await this.loadPMSummary();
    },
    async deleteSubmittal(id) {
      if (!confirm('Delete?')) return;
      await this.delete('/api/pm/submittals/' + id);
      await this.loadSubmittals();
    },

    // Meetings
    async loadMeetings() {
      if (!this.currentProject) return;
      this.pmMeetingsLoading = true;
      try { this.pmMeetings = await this.get('/api/pm/meetings?' + this._pmParams()); }
      catch(e) { this.pmMeetings = []; }
      finally { this.pmMeetingsLoading = false; }
    },
    openMeetingModal(m = null) {
      this.editingMeeting = m;
      this.meetingForm = m ? { title: m.title, meeting_date: m.meeting_date||'',
        location: m.location||'', attendees: m.attendees||'', agenda: m.agenda||'',
        minutes: m.minutes||'', action_items: m.action_items||'', next_meeting: m.next_meeting||'' }
        : { title:'', meeting_date: new Date().toISOString().slice(0,10),
            location:'', attendees:'', agenda:'', minutes:'', action_items:'', next_meeting:'' };
      this.showMeetingModal = true;
    },
    async saveMeeting() {
      const body = { ...this.meetingForm, project_id: this.currentProject?.id };
      if (this.editingMeeting) await this.put('/api/pm/meetings/' + this.editingMeeting.id, body);
      else await this.post('/api/pm/meetings', body);
      this.showMeetingModal = false;
      await this.loadMeetings();
    },
    async deleteMeeting(id) {
      if (!confirm('Delete this meeting record?')) return;
      await this.delete('/api/pm/meetings/' + id);
      await this.loadMeetings();
    },

    // Photos
    async loadPhotos() {
      if (!this.currentProject) return;
      this.pmPhotosLoading = true;
      try { this.pmPhotos = await this.get('/api/pm/photos?' + this._pmParams()); }
      catch(e) { this.pmPhotos = []; }
      finally { this.pmPhotosLoading = false; }
    },
    async uploadPhoto(files) {
      if (!files || !files.length) return;
      for (const file of files) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('project_id', this.currentProject?.id);
        fd.append('category', 'progress');
        fd.append('taken_date', new Date().toISOString().slice(0,10));
        const r = await fetch('/api/pm/photos?' + new URLSearchParams({ project_id: this.currentProject?.id, category:'progress', taken_date: new Date().toISOString().slice(0,10) }), {
          method: 'POST', headers: this._headers(), body: fd,
        });
        if (!r.ok) { const e = await r.json(); alert(e.detail || 'Upload failed'); }
      }
      await this.loadPhotos(); await this.loadPMSummary();
    },
    async deletePhoto(id) {
      if (!confirm('Delete this photo?')) return;
      await this.delete('/api/pm/photos/' + id);
      await this.loadPhotos();
    },

    // ── Audit log ─────────────────────────────────────────────────
    async loadAuditLog(page = 1) {
      this.auditLoading = true;
      try {
        const data = await this.get(`/api/audit?page=${page}&limit=50`);
        this.auditLog = data.items || [];
        this.auditTotal = data.total || 0;
        this.auditPage = page;
      } catch(e) { this.auditLog = []; }
      finally { this.auditLoading = false; }
    },

    // ── Super Admin functions ─────────────────────────────────────
    async superAdminCreateOrg() {
      this.createOrgLoading = true; this.createOrgError = '';
      try {
        await this.post('/api/org/admin/create', this.createOrgForm);
        this.showCreateOrgModal = false;
        this.createOrgForm = { name: '', owner_username: '', plan: 'starter' };
        await this.loadAllOrgs();
      } catch(e) { this.createOrgError = e.message; }
      finally { this.createOrgLoading = false; }
    },
    async superAdminChangePlan(orgId, plan) {
      try {
        await fetch('/api/org/admin/' + orgId + '/plan', {
          method: 'PUT',
          headers: { ...this._headers(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan }),
        });
        const o = this.allOrgsList.find(x => x.id === orgId);
        if (o) o.plan = plan;
      } catch(e) { alert('Failed to update plan: ' + e.message); }
    },
    async superAdminViewMembers(org) {
      this.selectedOrgForAdmin = org;
      this.orgMembersList = [];
      this.showOrgMembersModal = true;
      try {
        const data = await fetch('/api/org/admin/' + org.id + '/members', { headers: this._headers() });
        this.orgMembersList = await data.json();
      } catch(e) { this.orgMembersList = []; }
    },
    superAdminSendInvite(org) {
      this.selectedOrgForAdmin = org;
      this.saInviteEmail = ''; this.saInviteRole = 'editor';
      this.saInviteMsg = ''; this.saInviteErr = false;
      this.showSuperAdminInviteModal = true;
    },
    async superAdminDoInvite() {
      this.saInviteLoading = true; this.saInviteMsg = ''; this.saInviteErr = false;
      try {
        const r = await fetch('/api/org/admin/' + this.selectedOrgForAdmin.id + '/invite', {
          method: 'POST',
          headers: { ...this._headers(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: this.saInviteEmail, role: this.saInviteRole }),
        });
        const d = await r.json();
        if (!r.ok) { this.saInviteErr = true; this.saInviteMsg = d.detail || 'Failed'; }
        else { this.saInviteMsg = d.message || 'Invitation sent!'; }
      } catch(e) { this.saInviteErr = true; this.saInviteMsg = e.message; }
      finally { this.saInviteLoading = false; }
    },

    // ── Org invitations ───────────────────────────────────────────
    async sendInvite() {
      this.inviteLoading = true; this.inviteMsg = ''; this.inviteError = '';
      try {
        const r = await this.post('/api/org/invite', this.inviteForm);
        this.inviteMsg = r.message || 'Invitation sent!';
        this.inviteForm = { email: '', role: 'editor' };
        await this.loadPendingInvites();
      } catch(e) { this.inviteError = e.message; }
      finally { this.inviteLoading = false; }
    },
    async loadPendingInvites() {
      try { this.pendingInvites = await this.get('/api/org/invitations'); } catch(e) { this.pendingInvites = []; }
    },
    async cancelInvite(id) {
      if(!confirm('Cancel this invitation?')) return;
      try { await this.delete(`/api/org/invitations/${id}`); await this.loadPendingInvites(); } catch(e) {}
    },

    // ── Safety Incidents ────────────────────────────────────────────
    async loadSafetyIncidents() {
      if (!this.currentProject) return;
      this.safetyLoading = true;
      try {
        const [incidents, summary] = await Promise.all([
          this.get(`/api/project/${this.currentProject.id}/safety/incidents`),
          this.get(`/api/project/${this.currentProject.id}/safety/summary`),
        ]);
        this.safetyIncidents = incidents;
        this.safetySummary = summary;
      } catch(e) { this.safetyIncidents = []; }
      finally { this.safetyLoading = false; }
    },
    editSafetyIncident(inc) {
      this.safetyEditId = inc.id;
      this.safetyForm = { incident_date:inc.incident_date, incident_type:inc.incident_type, severity:inc.severity, description:inc.description, location:inc.location||'', persons_involved:inc.persons_involved||'', immediate_actions:inc.immediate_actions||'', wsib_reportable:inc.wsib_reportable, mol_reportable:inc.mol_reportable, status:inc.status };
      this.showSafetyModal = true;
    },
    async saveSafetyIncident() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.safetyEditId) await this.put(`/api/project/${pid}/safety/incidents/${this.safetyEditId}`, this.safetyForm);
        else await this.post(`/api/project/${pid}/safety/incidents`, this.safetyForm);
        this.showSafetyModal = false; this.safetyEditId = null;
        await this.loadSafetyIncidents();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteSafetyIncident(id) {
      if (!confirm('Delete this incident?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/safety/incidents/${id}`); await this.loadSafetyIncidents(); } catch(e) {}
    },

    // ── Toolbox Talks ───────────────────────────────────────────────
    async loadToolboxTalks() {
      if (!this.currentProject) return;
      this.toolboxLoading = true;
      try { this.toolboxTalks = await this.get(`/api/project/${this.currentProject.id}/safety/toolbox-talks`); } catch(e) { this.toolboxTalks = []; }
      finally { this.toolboxLoading = false; }
    },
    editToolboxTalk(t) {
      this.toolboxEditId = t.id;
      this.toolboxForm = { talk_date:t.talk_date, topic:t.topic, facilitator:t.facilitator||'', attendee_count:t.attendee_count||0, attendees:t.attendees||'', duration_minutes:t.duration_minutes||'', notes:t.notes||'' };
      this.showToolboxModal = true;
    },
    async saveToolboxTalk() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.toolboxEditId) await this.put(`/api/project/${pid}/safety/toolbox-talks/${this.toolboxEditId}`, this.toolboxForm);
        else await this.post(`/api/project/${pid}/safety/toolbox-talks`, this.toolboxForm);
        this.showToolboxModal = false; this.toolboxEditId = null;
        await this.loadToolboxTalks();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteToolboxTalk(id) {
      if (!confirm('Delete this talk record?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/safety/toolbox-talks/${id}`); await this.loadToolboxTalks(); } catch(e) {}
    },

    // ── Permits ─────────────────────────────────────────────────────
    async loadPermits() {
      if (!this.currentProject) return;
      this.permitsLoading = true;
      try { this.permitsData = await this.get(`/api/project/${this.currentProject.id}/permits`); } catch(e) { this.permitsData = []; }
      finally { this.permitsLoading = false; }
    },
    editPermit(p) {
      this.permitEditId = p.id;
      this.permitForm = { permit_type:p.permit_type, permit_number:p.permit_number||'', description:p.description, authority:p.authority||'', application_date:p.application_date||'', issued_date:p.issued_date||'', expiry_date:p.expiry_date||'', status:p.status, fee_paid:p.fee_paid||'', notes:p.notes||'' };
      this.permitFormError = ''; this.showPermitModal = true;
    },
    async savePermit() {
      if (!this.currentProject) return;
      if (!this.permitForm.description.trim()) { this.permitFormError = 'Description is required'; return; }
      const pid = this.currentProject.id;
      try {
        if (this.permitEditId) await this.put(`/api/project/${pid}/permits/${this.permitEditId}`, this.permitForm);
        else await this.post(`/api/project/${pid}/permits`, this.permitForm);
        this.showPermitModal = false; this.permitEditId = null;
        await this.loadPermits();
      } catch(e) { this.permitFormError = e.message||'Save failed'; }
    },
    async deletePermit(id) {
      if (!confirm('Delete this permit?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/permits/${id}`); await this.loadPermits(); } catch(e) {}
    },
    async openPermitInspections(p) {
      this.activePermitForInsp = p;
      this.inspForm = { inspection_type:'', result:'pending', scheduled_date:'', completed_date:'', inspector_name:'', deficiencies:'' };
      try { this.permitInspections = await this.get(`/api/project/${this.currentProject.id}/permits/${p.id}/inspections`); } catch(e) { this.permitInspections = []; }
      this.showPermitInspModal = true;
    },
    async savePermitInspection() {
      if (!this.currentProject || !this.activePermitForInsp) return;
      if (!this.inspForm.inspection_type.trim()) { alert('Inspection type is required'); return; }
      try {
        await this.post(`/api/project/${this.currentProject.id}/permits/${this.activePermitForInsp.id}/inspections`, this.inspForm);
        this.permitInspections = await this.get(`/api/project/${this.currentProject.id}/permits/${this.activePermitForInsp.id}/inspections`);
        this.inspForm = { inspection_type:'', result:'pending', scheduled_date:'', completed_date:'', inspector_name:'', deficiencies:'' };
        await this.loadPermits();
      } catch(e) { alert(e.message||'Save failed'); }
    },

    // ── Warranty ────────────────────────────────────────────────────
    async loadWarranty() {
      if (!this.currentProject) return;
      this.warrantyLoading = true;
      try { this.warrantyItems = await this.get(`/api/project/${this.currentProject.id}/warranty`); } catch(e) { this.warrantyItems = []; }
      finally { this.warrantyLoading = false; }
    },
    editWarranty(w) {
      this.warrantyEditId = w.id;
      this.warrantyForm = { category:w.category, description:w.description, location:w.location||'', reported_date:w.reported_date||'', warranty_type:w.warranty_type, homeowner_name:w.homeowner_name||'', status:w.status, assigned_to:w.assigned_to||'', scheduled_date:w.scheduled_date||'', notes:w.notes||'' };
      this.showWarrantyModal = true;
    },
    async saveWarranty() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.warrantyEditId) await this.put(`/api/project/${pid}/warranty/${this.warrantyEditId}`, this.warrantyForm);
        else await this.post(`/api/project/${pid}/warranty`, this.warrantyForm);
        this.showWarrantyModal = false; this.warrantyEditId = null;
        await this.loadWarranty();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteWarranty(id) {
      if (!confirm('Delete this warranty item?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/warranty/${id}`); await this.loadWarranty(); } catch(e) {}
    },

    // ── Labour / Timecards ──────────────────────────────────────────
    async loadTimecards() {
      if (!this.currentProject) return;
      this.timecardsLoading = true;
      try {
        const [tcs, report] = await Promise.all([
          this.get(`/api/project/${this.currentProject.id}/timecards`),
          this.get(`/api/project/${this.currentProject.id}/labour-report`),
        ]);
        this.timecards = tcs; this.labourReport = report;
      } catch(e) { this.timecards = []; }
      finally { this.timecardsLoading = false; }
    },
    async loadLabourReport() {
      if (!this.currentProject) return;
      try { this.labourReport = await this.get(`/api/project/${this.currentProject.id}/labour-report`); } catch(e) {}
    },
    editTimecard(tc) {
      this.timecardEditId = tc.id;
      this.timecardForm = { worker_name:tc.worker_name, trade:tc.trade||'', classification:tc.classification||'', work_date:tc.work_date, regular_hours:tc.regular_hours, overtime_hours:tc.overtime_hours, double_time_hours:tc.double_time_hours, hourly_rate:tc.hourly_rate||'', burden_pct:tc.burden_pct||0, work_description:tc.work_description||'' };
      this.showTimecardModal = true;
    },
    async saveTimecard() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.timecardEditId) await this.put(`/api/project/${pid}/timecards/${this.timecardEditId}`, this.timecardForm);
        else await this.post(`/api/project/${pid}/timecards`, this.timecardForm);
        this.showTimecardModal = false; this.timecardEditId = null;
        await this.loadTimecards();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteTimecard(id) {
      if (!confirm('Delete this timecard?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/timecards/${id}`); await this.loadTimecards(); } catch(e) {}
    },

    // ── WIP Report ──────────────────────────────────────────────────
    async loadWIPReport() {
      if (!this.currentProject) return;
      this.wipLoading = true;
      try { this.wipData = await this.get(`/api/project/${this.currentProject.id}/wip-report`); } catch(e) { this.wipData = null; }
      finally { this.wipLoading = false; }
    },

    // ── Covenants ───────────────────────────────────────────────────
    async loadCovenants() {
      if (!this.currentProject) return;
      this.covenantsLoading = true;
      try { this.covenantsData = await this.get(`/api/project/${this.currentProject.id}/covenants`); } catch(e) { this.covenantsData = []; }
      finally { this.covenantsLoading = false; }
    },
    editCovenant(c) {
      this.covenantEditId = c.id;
      this.covenantForm = { covenant_type:c.covenant_type, name:c.name, threshold_value:c.threshold_value??'', threshold_operator:c.threshold_operator, current_value:c.current_value??'', as_of_date:c.as_of_date||'', status:c.status, notes:c.notes||'' };
      this.showCovenantModal = true;
    },
    async saveCovenant() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.covenantEditId) await this.put(`/api/project/${pid}/covenants/${this.covenantEditId}`, this.covenantForm);
        else await this.post(`/api/project/${pid}/covenants`, this.covenantForm);
        this.showCovenantModal = false; this.covenantEditId = null;
        await this.loadCovenants();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteCovenant(id) {
      if (!confirm('Delete this covenant?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/covenants/${id}`); await this.loadCovenants(); } catch(e) {}
    },
    async openCreditCommittee() {
      if (!this.currentProject) return;
      try {
        const r = await fetch(`/api/project/${this.currentProject.id}/credit-committee-report`, { headers: { Authorization: 'Bearer ' + this.token } });
        if (!r.ok) throw new Error('Failed to generate report');
        const html = await r.text();
        const blob = new Blob([html], { type: 'text/html' });
        window.open(URL.createObjectURL(blob), '_blank');
      } catch(e) { alert(e.message||'Could not open report'); }
    },

    // ── Interest Reserve ────────────────────────────────────────────
    async loadInterestReserve() {
      if (!this.currentProject) return;
      this.irLoading = true;
      try { this.interestReserve = await this.get(`/api/project/${this.currentProject.id}/interest-reserve`); } catch(e) { this.interestReserve = null; }
      finally { this.irLoading = false; }
    },
    async saveInterestReserve() {
      if (!this.currentProject) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/interest-reserve`, this.irForm);
        this.showIRModal = false;
        await this.loadInterestReserve();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async addIRDraw() {
      if (!this.currentProject) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/interest-reserve/draws`, this.irDrawForm);
        this.showIRDrawModal = false;
        await this.loadInterestReserve();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteIRDraw(id) {
      if (!confirm('Delete this reserve draw?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/interest-reserve/draws/${id}`); await this.loadInterestReserve(); } catch(e) {}
    },

    // ── Bonds ────────────────────────────────────────────────────────
    async loadBonds() {
      if (!this.currentProject) return;
      this.bondsLoading = true;
      try { this.bondsData = await this.get(`/api/project/${this.currentProject.id}/bonds`); } catch(e) { this.bondsData = []; }
      finally { this.bondsLoading = false; }
    },
    editBond(b) {
      this.bondEditId = b.id;
      this.bondForm = { vendor_name:b.vendor_name||'', bond_type:b.bond_type, bond_number:b.bond_number||'', surety_company:b.surety_company||'', bond_amount:b.bond_amount||'', effective_date:b.effective_date||'', expiry_date:b.expiry_date||'', status:b.status, notes:b.notes||'' };
      this.showBondModal = true;
    },
    async saveBond() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.bondEditId) await this.put(`/api/project/${pid}/bonds/${this.bondEditId}`, this.bondForm);
        else await this.post(`/api/project/${pid}/bonds`, this.bondForm);
        this.showBondModal = false; this.bondEditId = null;
        await this.loadBonds();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteBond(id) {
      if (!confirm('Delete this bond record?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/bonds/${id}`); await this.loadBonds(); } catch(e) {}
    },

    // ── Bid Management ──────────────────────────────────────────────
    async loadBidPackages() {
      if (!this.currentProject) return;
      this.bidPkgsLoading = true;
      try { this.bidPackages = await this.get(`/api/project/${this.currentProject.id}/bid-packages`); } catch(e) { this.bidPackages = []; }
      finally { this.bidPkgsLoading = false; }
    },
    editBidPackage(p) {
      this.bidPkgEditId = p.id;
      this.bidPkgForm = { title:p.title, trade_category:p.trade_category||'', issue_date:p.issue_date||'', due_date:p.due_date||'', estimated_value:p.estimated_value||'', status:p.status, description:p.description||'', notes:p.notes||'' };
      this.showBidPkgModal = true;
    },
    async saveBidPackage() {
      if (!this.currentProject || !this.bidPkgForm.title.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.bidPkgEditId) await this.put(`/api/project/${pid}/bid-packages/${this.bidPkgEditId}`, this.bidPkgForm);
        else await this.post(`/api/project/${pid}/bid-packages`, this.bidPkgForm);
        this.showBidPkgModal = false; this.bidPkgEditId = null;
        await this.loadBidPackages();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async openBidPackage(pkg) {
      this.activeBidPackage = pkg;
      this.view = 'bid-detail';
      try {
        const [responses, leveling] = await Promise.all([
          this.get(`/api/project/${this.currentProject.id}/bid-packages/${pkg.id}/responses`),
          this.get(`/api/project/${this.currentProject.id}/bid-packages/${pkg.id}/leveling`),
        ]);
        this.bidResponses = responses;
        this.bidLeveling = leveling;
      } catch(e) { this.bidResponses = []; this.bidLeveling = null; }
    },
    editBidResponse(r) {
      this.bidRespEditId = r.id;
      this.bidRespForm = { vendor_name:r.vendor_name, contact_email:r.contact_email||'', total_amount:r.total_amount||'', inclusions:r.inclusions||'', exclusions:r.exclusions||'', qualifications:r.qualifications||'', status:r.status, notes:r.notes||'' };
      this.showBidRespModal = true;
    },
    async saveBidResponse() {
      if (!this.activeBidPackage) return;
      const pid = this.currentProject.id;
      const pkgId = this.activeBidPackage.id;
      try {
        if (this.bidRespEditId) await this.put(`/api/project/${pid}/bid-packages/${pkgId}/responses/${this.bidRespEditId}`, this.bidRespForm);
        else await this.post(`/api/project/${pid}/bid-packages/${pkgId}/responses`, this.bidRespForm);
        this.showBidRespModal = false; this.bidRespEditId = null;
        await this.openBidPackage(this.activeBidPackage);
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteBidResponse(id) {
      if (!confirm('Delete this bid response?')) return;
      try {
        await this.delete(`/api/project/${this.currentProject.id}/bid-packages/${this.activeBidPackage.id}/responses/${id}`);
        await this.openBidPackage(this.activeBidPackage);
      } catch(e) {}
    },

    // ── Portfolio Risk ───────────────────────────────────────────────
    async loadPortfolioRisk() {
      this.portfolioRiskLoading = true;
      try { this.portfolioRisk = await this.get('/api/portfolio/risk-dashboard'); } catch(e) { this.portfolioRisk = null; }
      finally { this.portfolioRiskLoading = false; }
    },
    async switchToProject(p) {
      const proj = this.projects.find(x => x.id === p.id);
      if (proj) { await this.selectProject(proj); this.view = 'dashboard'; }
    },

    // ── AI Risk Score ────────────────────────────────────────────────
    async loadAIRiskScore() {
      if (!this.currentProject) return;
      this.aiRiskLoading = true;
      try { this.aiRiskData = await this.get(`/api/project/${this.currentProject.id}/ai-risk-score`); } catch(e) { this.aiRiskData = null; }
      finally { this.aiRiskLoading = false; }
    },

    // ── Cash Flow S-Curve ────────────────────────────────────────────
    async loadScurve() {
      if (!this.currentProject) return;
      this.scurveLoading = true;
      try { this.scurveData = await this.get(`/api/project/${this.currentProject.id}/cash-flow-scurve`); } catch(e) { this.scurveData = null; }
      finally { this.scurveLoading = false; }
    },

    // ── Sub Prequalification ─────────────────────────────────────────
    async loadPrequals() {
      this.prequalsLoading = true;
      try { this.prequals = await this.get('/api/prequal/'); } catch(e) { this.prequals = []; }
      finally { this.prequalsLoading = false; }
    },
    async sendPrequalInvite() {
      const trade = prompt('Trade / Division (e.g. Electrical, Framing):') || '';
      const email = prompt('Sub contact email (optional):') || '';
      try {
        const r = await this.post('/api/prequal/invite', { trade, contact_email: email });
        await navigator.clipboard.writeText(window.location.origin + r.portal_url);
        alert('Invite link copied to clipboard! Share with the subcontractor.');
        await this.loadPrequals();
      } catch(e) { alert(e.message||'Failed to create invite'); }
    },
    async approvePrequal(id, status) {
      try { await this.put(`/api/prequal/${id}/status`, { status }); await this.loadPrequals(); } catch(e) {}
    },
    async deletePrequal(id) {
      if (!confirm('Delete this prequalification?')) return;
      try { await this.delete(`/api/prequal/${id}`); await this.loadPrequals(); } catch(e) {}
    },
    copyPrequalLink(url) {
      if (url) navigator.clipboard.writeText(window.location.origin + url).then(() => alert('Link copied!')).catch(() => prompt('Copy this link:', window.location.origin + url));
    },

    // ── Client Hub ───────────────────────────────────────────────────
    async loadHubPosts() {
      if (!this.currentProject) return;
      try { this.hubPosts = await this.get(`/api/project/${this.currentProject.id}/hub/posts`); } catch(e) { this.hubPosts = []; }
    },
    async loadHubMessages() {
      if (!this.currentProject) return;
      try { this.hubMessages = await this.get(`/api/project/${this.currentProject.id}/hub/messages`); } catch(e) { this.hubMessages = []; }
    },
    async saveHubPost() {
      if (!this.currentProject || !this.hubPostForm.title.trim()) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/hub/posts`, this.hubPostForm);
        this.showHubPostModal = false;
        await this.loadHubPosts();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteHubPost(id) {
      if (!confirm('Delete this update?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/hub/posts/${id}`); await this.loadHubPosts(); } catch(e) {}
    },
    async sendHubMessage() {
      if (!this.currentProject || !this.hubNewMessage.trim()) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/hub/messages`, { message: this.hubNewMessage });
        this.hubNewMessage = '';
        await this.loadHubMessages();
      } catch(e) {}
    },

    // ── Drawing Register ─────────────────────────────────────────────
    async loadDrawings() {
      if (!this.currentProject) return;
      this.drawingsLoading = true;
      try { this.drawings = await this.get(`/api/project/${this.currentProject.id}/drawings`); } catch(e) { this.drawings = []; }
      finally { this.drawingsLoading = false; }
    },
    editDrawing(d) {
      this.drawingEditId = d.id;
      this.drawingForm = { drawing_number:d.drawing_number, title:d.title, discipline:d.discipline||'', current_revision:d.current_revision||'', revision_date:d.revision_date||'', status:d.status, notes:d.notes||'' };
      this.showDrawingModal = true;
    },
    async saveDrawing() {
      if (!this.currentProject || !this.drawingForm.drawing_number.trim() || !this.drawingForm.title.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.drawingEditId) await this.put(`/api/project/${pid}/drawings/${this.drawingEditId}`, this.drawingForm);
        else await this.post(`/api/project/${pid}/drawings`, this.drawingForm);
        this.showDrawingModal = false; this.drawingEditId = null;
        await this.loadDrawings();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteDrawing(id) {
      if (!confirm('Delete this drawing?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/drawings/${id}`); await this.loadDrawings(); } catch(e) {}
    },

    // ── AI Spec Review ───────────────────────────────────────────────
    async loadSpecReviews() {
      if (!this.currentProject) return;
      try { this.specReviews = await this.get(`/api/project/${this.currentProject.id}/spec-reviews`); } catch(e) { this.specReviews = []; }
    },
    async uploadSpec(file) {
      if (!file || !this.currentProject) return;
      this.specReviewLoading = true;
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await fetch(`/api/project/${this.currentProject.id}/spec-reviews/analyze`, {
          method: 'POST', headers: { Authorization: 'Bearer ' + this.token }, body: fd
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Analysis failed');
        await this.loadSpecReviews();
      } catch(e) { alert(e.message||'Spec analysis failed'); }
      finally { this.specReviewLoading = false; }
    },
    async deleteSpecReview(id) {
      if (!confirm('Delete this review?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/spec-reviews/${id}`); await this.loadSpecReviews(); } catch(e) {}
    },

    // ── Union Compliance ─────────────────────────────────────────────
    async loadUnions() {
      if (!this.currentProject) return;
      this.unionsLoading = true;
      try { this.unions = await this.get(`/api/project/${this.currentProject.id}/unions`); } catch(e) { this.unions = []; }
      finally { this.unionsLoading = false; }
    },
    editUnion(u) {
      this.unionEditId = u.id;
      this.unionForm = { trade:u.trade, local_number:u.local_number||'', agreement_type:u.agreement_type, apprentice_ratio:u.apprentice_ratio||'', journeymen_count:u.journeymen_count||0, apprentice_count:u.apprentice_count||0, expiry_date:u.expiry_date||'', notes:u.notes||'' };
      this.showUnionModal = true;
    },
    async saveUnion() {
      if (!this.currentProject || !this.unionForm.trade.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.unionEditId) await this.put(`/api/project/${pid}/unions/${this.unionEditId}`, this.unionForm);
        else await this.post(`/api/project/${pid}/unions`, this.unionForm);
        this.showUnionModal = false; this.unionEditId = null;
        await this.loadUnions();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteUnion(id) {
      if (!confirm('Delete this union record?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/unions/${id}`); await this.loadUnions(); } catch(e) {}
    },

    // ── Project Closeout ─────────────────────────────────────────────
    async loadCloseout() {
      if (!this.currentProject) return;
      this.closeoutLoading = true;
      try {
        const [items, summary] = await Promise.all([
          this.get(`/api/project/${this.currentProject.id}/closeout`),
          this.get(`/api/project/${this.currentProject.id}/closeout/summary`),
        ]);
        this.closeoutItems = items; this.closeoutSummary = summary;
      } catch(e) { this.closeoutItems = []; }
      finally { this.closeoutLoading = false; }
    },
    async seedCloseout() {
      if (!this.currentProject) return;
      try { await this.post(`/api/project/${this.currentProject.id}/closeout/seed`, {}); await this.loadCloseout(); } catch(e) { alert(e.message); }
    },
    async toggleCloseoutItem(item, checked) {
      try {
        await this.put(`/api/project/${this.currentProject.id}/closeout/${item.id}`, { status: checked ? 'complete' : 'pending' });
        await this.loadCloseout();
      } catch(e) {}
    },
    async saveCloseoutItem() {
      if (!this.currentProject || !this.closeoutForm.item_name.trim()) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/closeout`, this.closeoutForm);
        this.showCloseoutModal = false;
        await this.loadCloseout();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteCloseoutItem(id) {
      try { await this.delete(`/api/project/${this.currentProject.id}/closeout/${id}`); await this.loadCloseout(); } catch(e) {}
    },

    // ── CRM ──────────────────────────────────────────────────────────
    async loadCRMLeads() {
      this.crmLoading = true;
      try {
        const [leads, pipeline] = await Promise.all([
          this.get('/api/crm/leads'), this.get('/api/crm/pipeline'),
        ]);
        this.crmLeads = leads; this.crmPipeline = pipeline;
      } catch(e) { this.crmLeads = []; }
      finally { this.crmLoading = false; }
    },
    async saveLead() {
      try {
        if (this.leadEditId) await this.put(`/api/crm/leads/${this.leadEditId}`, this.leadForm);
        else await this.post('/api/crm/leads', this.leadForm);
        this.showLeadModal = false; this.leadEditId = null;
        await this.loadCRMLeads();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    editLead(l) {
      this.leadEditId = l.id;
      this.leadForm = { company_name:l.company_name, contact_name:l.contact_name||'', contact_email:l.contact_email||'', contact_phone:l.contact_phone||'', project_type:l.project_type||'commercial', estimated_value:l.estimated_value||'', location:l.location||'', status:l.status, source:l.source, probability_pct:l.probability_pct, expected_close_date:l.expected_close_date||'', next_action:l.next_action||'', notes:l.notes||'' };
      this.showLeadModal = true;
    },
    async deleteLead(id) {
      if (!confirm('Delete this lead?')) return;
      try { await this.delete(`/api/crm/leads/${id}`); await this.loadCRMLeads(); } catch(e) {}
    },
    async loadAllProposals() {
      this.proposalsLoading = true;
      try { this.allProposals = await this.get('/api/crm/proposals'); } catch(e) { this.allProposals = []; }
      finally { this.proposalsLoading = false; }
    },
    copyProposalLink(url) {
      if (url) navigator.clipboard.writeText(window.location.origin + url).then(() => alert('Proposal link copied!')).catch(() => prompt('Copy:', window.location.origin + url));
    },

    // ── Cost Assemblies ────────────────────────────────────────────────
    async loadAssemblies() {
      this.assembliesLoading = true;
      try { this.assemblies = await this.get('/api/assemblies'); } catch(e) { this.assemblies = []; }
      finally { this.assembliesLoading = false; }
    },
    async saveAssembly() {
      try {
        const r = await this.post('/api/assemblies', this.assemblyForm);
        this.showAssemblyModal = false;
        await this.loadAssemblies();
        const asm = this.assemblies.find(a => a.id === r.id);
        if (asm) await this.openAssembly(asm);
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async openAssembly(asm) {
      this.activeAssembly = asm;
      try { const data = await this.get(`/api/assemblies/${asm.id}/items`); this.assemblyItems = data.items; } catch(e) { this.assemblyItems = []; }
    },
    async saveAssemblyItem() {
      if (!this.activeAssembly) return;
      try {
        await this.post(`/api/assemblies/${this.activeAssembly.id}/items`, this.asmItemForm);
        this.showAssemblyItemModal = false;
        await this.openAssembly(this.activeAssembly);
        await this.loadAssemblies();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async applyAssemblyToEstimate() {
      if (!this.activeAssembly || !this.activeEstimate) return;
      const multiplier = parseFloat(prompt(`Multiplier for "${this.activeAssembly.name}" (e.g. 1.5 for 1.5x quantities):`) || '1');
      if (isNaN(multiplier) || multiplier <= 0) return;
      try {
        const r = await this.post(`/api/assemblies/${this.activeAssembly.id}/apply-to-estimate/${this.activeEstimate.id}`, { multiplier });
        alert(`✓ Added ${r.added} line items to estimate.`);
        await this.openEstimate(this.activeEstimate);
      } catch(e) { alert(e.message||'Failed'); }
    },

    // ── Procurement ────────────────────────────────────────────────────
    async loadProcurement() {
      if (!this.currentProject) return;
      this.procurementLoading = true;
      try { this.procurementItems = await this.get(`/api/project/${this.currentProject.id}/procurement`); } catch(e) { this.procurementItems = []; }
      finally { this.procurementLoading = false; }
    },
    async saveProcurement() {
      if (!this.currentProject || !this.procForm.item_name.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.procEditId) await this.put(`/api/project/${pid}/procurement/${this.procEditId}`, this.procForm);
        else await this.post(`/api/project/${pid}/procurement`, this.procForm);
        this.showProcurementModal = false; this.procEditId = null;
        await this.loadProcurement();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    editProcurement(i) {
      this.procEditId = i.id;
      this.procForm = { item_name:i.item_name, vendor_name:i.vendor_name||'', category:i.category, lead_time_weeks:i.lead_time_weeks||'', order_date:i.order_date||'', required_on_site_date:i.required_on_site_date||'', total_cost:i.total_cost||'', status:i.status, notes:i.notes||'' };
      this.showProcurementModal = true;
    },
    async deleteProcurement(id) {
      if (!confirm('Delete this item?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/procurement/${id}`); await this.loadProcurement(); } catch(e) {}
    },

    // ── VE Log ────────────────────────────────────────────────────────
    async loadVELog() {
      if (!this.currentProject) return;
      this.veLoading = true;
      try { const data = await this.get(`/api/project/${this.currentProject.id}/ve-log`); this.veItems = data.items; this.veSummary = data.summary; } catch(e) { this.veItems = []; }
      finally { this.veLoading = false; }
    },
    async saveVE() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.veEditId) await this.put(`/api/project/${pid}/ve-log/${this.veEditId}`, this.veForm);
        else await this.post(`/api/project/${pid}/ve-log`, this.veForm);
        this.showVEModal = false; this.veEditId = null;
        await this.loadVELog();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    editVE(i) {
      this.veEditId = i.id;
      this.veForm = { description:i.description, original_spec:i.original_spec||'', proposed_alternate:i.proposed_alternate||'', original_cost:i.original_cost||'', alternate_cost:i.alternate_cost||'', status:i.status, notes:i.notes||'' };
      this.showVEModal = true;
    },
    async deleteVE(id) {
      if (!confirm('Delete this VE item?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/ve-log/${id}`); await this.loadVELog(); } catch(e) {}
    },

    // ── CCDC Contracts ─────────────────────────────────────────────────
    async loadCCDCContracts() {
      if (!this.currentProject) return;
      this.ccdcLoading = true;
      try { this.ccdcContracts = await this.get(`/api/project/${this.currentProject.id}/ccdc-contracts`); } catch(e) { this.ccdcContracts = []; }
      finally { this.ccdcLoading = false; }
    },
    async saveCCDC() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.ccdcEditId) await this.put(`/api/project/${pid}/ccdc-contracts/${this.ccdcEditId}`, this.ccdcForm);
        else await this.post(`/api/project/${pid}/ccdc-contracts`, this.ccdcForm);
        this.showCCDCModal = false; this.ccdcEditId = null;
        await this.loadCCDCContracts();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteCCDC(id) {
      if (!confirm('Delete this contract?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/ccdc-contracts/${id}`); await this.loadCCDCContracts(); } catch(e) {}
    },

    // ── Units ──────────────────────────────────────────────────────────
    async loadUnits() {
      if (!this.currentProject) return;
      this.unitsLoading = true;
      try { this.unitData = await this.get(`/api/project/${this.currentProject.id}/units`); } catch(e) { this.unitData = null; }
      finally { this.unitsLoading = false; }
    },
    async saveUnit() {
      if (!this.currentProject || !this.unitForm.unit_number.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.unitEditId) await this.put(`/api/project/${pid}/units/${this.unitEditId}`, this.unitForm);
        else await this.post(`/api/project/${pid}/units`, this.unitForm);
        this.showUnitModal = false; this.unitEditId = null;
        await this.loadUnits();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    editUnit(u) {
      this.unitEditId = u.id;
      this.unitForm = { unit_number:u.unit_number, unit_type:u.unit_type||'2br', floor_area_sf:u.floor_area_sf||'', floor_number:u.floor_number||'', list_price:u.list_price||'', sale_price:u.sale_price||'', buyer_name:u.buyer_name||'', status:u.status, notes:u.notes||'' };
      this.showUnitModal = true;
    },
    async deleteUnit(id) {
      if (!confirm('Delete this unit?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/units/${id}`); await this.loadUnits(); } catch(e) {}
    },

    // ── Client Payments ────────────────────────────────────────────────
    async loadClientPayments() {
      if (!this.currentProject) return;
      this.clientPaymentsLoading = true;
      try { this.clientPayments = await this.get(`/api/project/${this.currentProject.id}/client-payments`); } catch(e) { this.clientPayments = []; }
      finally { this.clientPaymentsLoading = false; }
    },
    async saveClientPayment() {
      if (!this.currentProject || !this.cpForm.milestone_name.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.cpEditId) await this.put(`/api/project/${pid}/client-payments/${this.cpEditId}`, this.cpForm);
        else await this.post(`/api/project/${pid}/client-payments`, this.cpForm);
        this.showCPModal = false; this.cpEditId = null;
        await this.loadClientPayments();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    editClientPayment(i) {
      this.cpEditId = i.id;
      this.cpForm = { milestone_name:i.milestone_name, amount:i.amount||'', percentage_of_contract:i.percentage_of_contract||'', due_date:i.due_date||'', status:i.status, notes:i.notes||'' };
      this.showCPModal = true;
    },
    async deleteClientPayment(id) {
      try { await this.delete(`/api/project/${this.currentProject.id}/client-payments/${id}`); await this.loadClientPayments(); } catch(e) {}
    },

    // ── AI Spec Tools ──────────────────────────────────────────────────
    async askSpecQA() {
      if (!this.currentProject || !this.specQAQuestion.trim()) return;
      this.specQALoading = true; this.specQAResult = null;
      try {
        this.specQAResult = await this.post(`/api/project/${this.currentProject.id}/spec-qa`, { question: this.specQAQuestion, spec_context: this.specQAContext });
      } catch(e) { alert(e.message||'Q&A failed'); }
      finally { this.specQALoading = false; }
    },
    async generateRFI() {
      if (!this.currentProject || !this.rfiGenerateIssue.trim()) return;
      this.rfiGenerateLoading = true; this.rfiGenerateResult = null;
      try { this.rfiGenerateResult = await this.post(`/api/project/${this.currentProject.id}/generate-rfi`, { issue: this.rfiGenerateIssue }); } catch(e) { alert(e.message||'RFI generation failed'); }
      finally { this.rfiGenerateLoading = false; }
    },
    async importGeneratedRFI() {
      if (!this.rfiGenerateResult) return;
      try { const r = await this.post(`/api/project/${this.currentProject.id}/generate-rfi/import`, { rfi: this.rfiGenerateResult.rfi }); alert(`✓ RFI ${r.rfi_number} imported to RFI module.`); this.rfiGenerateResult = null; } catch(e) { alert(e.message||'Import failed'); }
    },
    async generateSubmittalLog(file) {
      if (!file || !this.currentProject) return;
      this.submittalGenLoading = true; this.submittalGenResult = null;
      const fd = new FormData(); fd.append('file', file);
      try {
        const r = await fetch(`/api/project/${this.currentProject.id}/generate-submittal-log`, { method:'POST', headers:{Authorization:'Bearer '+this.token}, body:fd });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail||'Failed');
        this.submittalGenResult = data;
      } catch(e) { alert(e.message||'Submittal generation failed'); }
      finally { this.submittalGenLoading = false; }
    },
    async importSubmittalLog() {
      if (!this.submittalGenResult) return;
      try { const r = await this.post(`/api/project/${this.currentProject.id}/generate-submittal-log/import`, { submittals: this.submittalGenResult.submittals }); alert(`✓ ${r.imported} submittals imported.`); this.view = 'pm-submittals'; await this.loadSubmittals(); } catch(e) { alert(e.message); }
    },

    // ── Advanced Reports ───────────────────────────────────────────────
    async loadAdvancedReport(report) {
      this.advReportView = report; this.advReportData = null; this.advReportLoading = true;
      const pid = this.currentProject?.id;
      try {
        if (report === 'cash-forecast' && pid) {
          this.cashForecastData = await this.get(`/api/reports/cash-forecast?project_id=${pid}&weeks_ahead=12`);
        } else if (report === 'forecast-accuracy' && pid) {
          this.forecastAccuracyData = await this.get(`/api/reports/forecast-accuracy/${pid}`);
        } else if (report === 'tax-reference') {
          this.advReportData = await this.get('/api/reports/tax-reference');
        } else if (report === 'sub-tier' && pid) {
          this.advReportData = await this.get(`/api/reports/sub-tier-payments/${pid}`);
        }
      } catch(e) { this.advReportData = null; }
      finally { this.advReportLoading = false; }
    },
    downloadWIPExcel() {
      const pid = this.currentProject?.id;
      const qs = pid ? `?project_id=${pid}` : '';
      window.open(`/api/reports/wip-schedule-excel${qs}`, '_blank');
    },
    downloadGLExport() {
      const pid = this.currentProject?.id;
      const qs = pid ? `?project_id=${pid}` : '';
      window.open(`/api/reports/gl-export${qs}`, '_blank');
    },

    // ── CFO Reports ──────────────────────────────────────────────────
    async loadCFOReport(report) {
      this.cfoReportView = report; this.cfoLoading = true; this.cfoData = null;
      const pid = this.currentProject?.id;
      const qs = pid ? `?project_id=${pid}` : '';
      try { this.cfoData = await this.get(`/api/reports/${report}${qs}`); } catch(e) { this.cfoData = null; }
      finally { this.cfoLoading = false; }
    },
    async generateLenderMemo() {
      if (!this.currentProject) return;
      this.aiLenderMemoLoading = true; this.aiLenderMemoData = null;
      try { this.aiLenderMemoData = await this.post(`/api/reports/ai-lender-memo/${this.currentProject.id}`, this.lenderMemoForm); }
      catch(e) { alert(e.message||'Memo generation failed'); }
      finally { this.aiLenderMemoLoading = false; }
    },
    copyLenderMemo() {
      if (this.aiLenderMemoData?.memo) {
        navigator.clipboard.writeText(this.aiLenderMemoData.memo).then(() => alert('Memo copied to clipboard!'));
      }
    },

    // ── Subcontracts ─────────────────────────────────────────────────
    async loadSubcontracts() {
      if (!this.currentProject) return;
      this.subcontractsLoading = true;
      try { this.subcontracts = await this.get(`/api/project/${this.currentProject.id}/subcontracts`); } catch(e) { this.subcontracts = []; }
      finally { this.subcontractsLoading = false; }
    },
    async saveSubcontract() {
      if (!this.currentProject || !this.subcontractForm.vendor_name.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.subcontractEditId) await this.put(`/api/project/${pid}/subcontracts/${this.subcontractEditId}`, this.subcontractForm);
        else await this.post(`/api/project/${pid}/subcontracts`, this.subcontractForm);
        this.showSubcontractModal = false; this.subcontractEditId = null;
        await this.loadSubcontracts();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteSubcontract(id) {
      if (!confirm('Delete this subcontract?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/subcontracts/${id}`); await this.loadSubcontracts(); } catch(e) {}
    },
    async previewSubcontract(sc) {
      try {
        const r = await this.get(`/api/project/${this.currentProject.id}/subcontracts/${sc.id}/html`);
        const blob = new Blob([r.html], {type:'text/html'}); window.open(URL.createObjectURL(blob), '_blank');
      } catch(e) { alert('Preview failed'); }
    },
    copySubcontractLink(url) {
      if (url) navigator.clipboard.writeText(window.location.origin + url).then(() => alert('Signature link copied!')).catch(() => prompt('Copy link:', window.location.origin + url));
    },

    // ── Sources & Uses ────────────────────────────────────────────────
    async loadSourcesUses() {
      if (!this.currentProject) return;
      this.sourcesUsesLoading = true;
      try { this.sourcesUses = await this.get(`/api/project/${this.currentProject.id}/sources-uses`); } catch(e) { this.sourcesUses = null; }
      finally { this.sourcesUsesLoading = false; }
    },
    async saveSUEntry() {
      if (!this.currentProject || !this.suForm.description.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.suEditId) await this.put(`/api/project/${pid}/sources-uses/${this.suEditId}`, this.suForm);
        else await this.post(`/api/project/${pid}/sources-uses`, this.suForm);
        this.showSUModal = false; this.suEditId = null;
        await this.loadSourcesUses();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteSUEntry(id) {
      try { await this.delete(`/api/project/${this.currentProject.id}/sources-uses/${id}`); await this.loadSourcesUses(); } catch(e) {}
    },

    // ── Estimating ────────────────────────────────────────────────────
    async loadEstimates() {
      if (!this.currentProject) return;
      this.estimatesLoading = true;
      try { this.estimates = await this.get(`/api/project/${this.currentProject.id}/estimates`); } catch(e) { this.estimates = []; }
      finally { this.estimatesLoading = false; }
    },
    async createEstimate() {
      if (!this.currentProject || !this.estimateForm.name.trim()) return;
      try {
        const r = await this.post(`/api/project/${this.currentProject.id}/estimates`, this.estimateForm);
        this.showEstimateModal = false;
        await this.loadEstimates();
        const est = this.estimates.find(e => e.id === r.id);
        if (est) await this.openEstimate(est);
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async openEstimate(est) {
      this.activeEstimate = est;
      try {
        const data = await this.get(`/api/project/${this.currentProject.id}/estimates/${est.id}/items`);
        this.estimateItems = data.items; this.estimateDivisions = data.by_division;
      } catch(e) { this.estimateItems = []; }
    },
    async saveEstimateItem() {
      if (!this.activeEstimate || !this.estItemForm.description.trim()) return;
      const pid = this.currentProject.id; const eid = this.activeEstimate.id;
      try {
        if (this.estItemEditId) await this.put(`/api/project/${pid}/estimates/${eid}/items/${this.estItemEditId}`, this.estItemForm);
        else await this.post(`/api/project/${pid}/estimates/${eid}/items`, this.estItemForm);
        this.showEstimateItemModal = false; this.estItemEditId = null;
        await this.openEstimate(this.activeEstimate);
        await this.loadEstimates();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteEstimateItem(id) {
      try { await this.delete(`/api/project/${this.currentProject.id}/estimates/${this.activeEstimate.id}/items/${id}`); await this.openEstimate(this.activeEstimate); } catch(e) {}
    },
    async convertEstimateToBudget() {
      if (!this.activeEstimate) return;
      if (!confirm('This will update your project cost categories and total budget from this estimate. Continue?')) return;
      try {
        const r = await this.post(`/api/project/${this.currentProject.id}/estimates/${this.activeEstimate.id}/convert-to-budget`, {});
        alert(`✓ ${r.created_categories} categories created, ${r.updated_categories} updated. Project budget set to $${r.total_budget.toLocaleString('en-CA',{maximumFractionDigits:0})}`);
        await this.loadProjectDashboard();
      } catch(e) { alert(e.message||'Conversion failed'); }
    },

    // ── Canadian Legal ─────────────────────────────────────────────────
    async loadNNPList() {
      if (!this.currentProject) return;
      try { this.nnpList = await this.get(`/api/project/${this.currentProject.id}/non-payment-notices`); } catch(e) { this.nnpList = []; }
    },
    async loadSPCerts() {
      if (!this.currentProject) return;
      try { this.spCerts = await this.get(`/api/project/${this.currentProject.id}/substantial-performance`); } catch(e) { this.spCerts = []; }
    },
    async saveNNP() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.nnpEditId) await this.put(`/api/project/${pid}/non-payment-notices/${this.nnpEditId}`, this.nnpForm);
        else await this.post(`/api/project/${pid}/non-payment-notices`, this.nnpForm);
        this.showNNPModal = false; this.nnpEditId = null;
        await this.loadNNPList();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async printNNP(id) {
      try {
        const r = await fetch(`/api/project/${this.currentProject.id}/non-payment-notices/${id}/html`, { headers: { Authorization: 'Bearer ' + this.token } });
        const html = await r.text();
        const w = window.open('', '_blank'); w.document.write(html); w.document.close();
      } catch(e) { alert('Print failed'); }
    },
    async saveSPCert() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.spEditId) await this.put(`/api/project/${pid}/substantial-performance/${this.spEditId}`, this.spForm);
        else await this.post(`/api/project/${pid}/substantial-performance`, this.spForm);
        this.showSPModal = false; this.spEditId = null;
        await this.loadSPCerts();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async validateProperInvoice() {
      if (!this.currentProject || !this.invoiceToValidate) return;
      try {
        this.invoiceValidationResult = await this.post(`/api/project/${this.currentProject.id}/validate-invoice/${this.invoiceToValidate}`, {});
      } catch(e) { alert(e.message||'Validation failed'); }
    },

    // ── Quality Inspections ────────────────────────────────────────────
    async loadQualityInspections() {
      if (!this.currentProject) return;
      this.qualityLoading = true;
      try { this.qualityInspections = await this.get(`/api/project/${this.currentProject.id}/quality-inspections`); } catch(e) { this.qualityInspections = []; }
      finally { this.qualityLoading = false; }
    },
    async createQualityInspection() {
      if (!this.currentProject || !this.qiForm.inspection_date) return;
      try {
        const r = await this.post(`/api/project/${this.currentProject.id}/quality-inspections`, this.qiForm);
        this.showQIModal = false;
        await this.loadQualityInspections();
        const insp = this.qualityInspections.find(i => i.id === r.id);
        if (insp) await this.openInspection(insp);
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async openInspection(insp) {
      this.activeInspection = insp; this.view = 'quality-detail';
      try {
        const data = await this.get(`/api/project/${this.currentProject.id}/quality-inspections/${insp.id}/items`);
        this.inspectionItems = data.items;
      } catch(e) { this.inspectionItems = []; }
    },
    async updateInspectionItem(item, result) {
      try {
        const r = await this.put(`/api/project/${this.currentProject.id}/quality-inspections/${this.activeInspection.id}/items/${item.id}`, { result });
        item.result = result;
        if (this.activeInspection) {
          this.activeInspection.pass_count = r.pass_count; this.activeInspection.fail_count = r.fail_count;
        }
      } catch(e) {}
    },

    // ── Visitor Log ────────────────────────────────────────────────────
    async loadVisitors() {
      if (!this.currentProject) return;
      this.visitorsLoading = true;
      try { this.visitors = await this.get(`/api/project/${this.currentProject.id}/visitors`); } catch(e) { this.visitors = []; }
      finally { this.visitorsLoading = false; }
    },
    async saveVisitor() {
      if (!this.currentProject || !this.visitorForm.visitor_name.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.visitorEditId) await this.put(`/api/project/${pid}/visitors/${this.visitorEditId}`, this.visitorForm);
        else await this.post(`/api/project/${pid}/visitors`, this.visitorForm);
        this.showVisitorModal = false; this.visitorEditId = null;
        await this.loadVisitors();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteVisitor(id) {
      try { await this.delete(`/api/project/${this.currentProject.id}/visitors/${id}`); await this.loadVisitors(); } catch(e) {}
    },

    // ── Loan Syndication ─────────────────────────────────────────────
    async loadSyndicates() {
      if (!this.currentProject) return;
      this.syndicatesLoading = true;
      try { this.syndicates = await this.get(`/api/project/${this.currentProject.id}/syndicates`); } catch(e) { this.syndicates = []; }
      finally { this.syndicatesLoading = false; }
    },
    editSyndicate(s) {
      this.syndicateEditId = s.id;
      this.syndicateForm = { facility_name:s.facility_name, total_commitment:s.total_commitment, currency:s.currency, lead_lender:s.lead_lender||'', closing_date:s.closing_date||'', maturity_date:s.maturity_date||'', interest_rate:s.interest_rate||'', notes:s.notes||'' };
      this.showSyndicateModal = true;
    },
    async saveSyndicate() {
      if (!this.currentProject || !this.syndicateForm.facility_name.trim()) return;
      const pid = this.currentProject.id;
      try {
        if (this.syndicateEditId) await this.put(`/api/project/${pid}/syndicates/${this.syndicateEditId}`, this.syndicateForm);
        else await this.post(`/api/project/${pid}/syndicates`, this.syndicateForm);
        this.showSyndicateModal = false; this.syndicateEditId = null;
        await this.loadSyndicates();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteSyndicate(id) {
      if (!confirm('Delete this loan facility?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/syndicates/${id}`); await this.loadSyndicates(); } catch(e) {}
    },
    async addSynParticipant() {
      const f = this.addParticipantForm;
      if (!f.lender_name.trim() || !f.participation_pct) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/syndicates/${f.syndicate_id}/participants`, f);
        this.showParticipantModal = false;
        await this.loadSyndicates();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteSynParticipant(synId, partId) {
      try { await this.delete(`/api/project/${this.currentProject.id}/syndicates/${synId}/participants/${partId}`); await this.loadSyndicates(); } catch(e) {}
    },
    async openDrawReport(syn) {
      try {
        const report = await this.get(`/api/project/${this.currentProject.id}/syndicates/${syn.id}/draw-report`);
        const html = `<html><head><title>Draw Report — ${syn.facility_name}</title>
<style>body{font-family:Arial;padding:24px}table{width:100%;border-collapse:collapse;margin-bottom:20px}th,td{border:1px solid #ddd;padding:8px 12px;text-align:left}th{background:#f5f5f5;font-size:12px}h2{font-size:18px}h3{font-size:14px;color:#666}</style></head><body>
<h2>${report.facility.name}</h2><p>Lead: ${report.facility.lead_lender||'—'} · Total: $${report.facility.total_commitment?.toLocaleString('en-CA',{maximumFractionDigits:0})}</p>
<h3>Cumulative Lender Positions</h3><table><tr><th>Lender</th><th>Share %</th><th>Total Approved Share</th><th>Commitment</th><th>Utilization</th></tr>
${report.cumulative.map(c=>`<tr><td>${c.lender}</td><td>${c.pct}%</td><td>$${c.total_approved_share?.toLocaleString('en-CA',{maximumFractionDigits:0})}</td><td>$${c.commitment?.toLocaleString('en-CA',{maximumFractionDigits:0})}</td><td>${c.utilization_pct}%</td></tr>`).join('')}
</table><h3>Draw-by-Draw Allocation</h3>
${report.draws.map(d=>`<h4>Draw #${d.draw_number} (${d.status}) — Submitted: $${d.total_submitted?.toLocaleString('en-CA',{maximumFractionDigits:0})} | Approved: $${d.total_approved?.toLocaleString('en-CA',{maximumFractionDigits:0})}</h4>
<table><tr><th>Lender</th><th>%</th><th>Submitted Share</th><th>Approved Share</th></tr>
${d.participant_shares?.map(p=>`<tr><td>${p.lender}</td><td>${p.pct}%</td><td>$${p.submitted_share?.toLocaleString('en-CA',{maximumFractionDigits:0})}</td><td>$${p.approved_share?.toLocaleString('en-CA',{maximumFractionDigits:0})}</td></tr>`).join('')}
</table>`).join('')}
</body></html>`;
        const blob = new Blob([html], {type:'text/html'});
        window.open(URL.createObjectURL(blob), '_blank');
      } catch(e) { alert('Could not load draw report: '+e.message); }
    },

    // ── ERP Integrations ─────────────────────────────────────────────
    async loadERPTypes() {
      try { this.erpTypes = await this.get('/api/erp/types'); } catch(e) { this.erpTypes = []; }
    },
    async loadERPCredentials() {
      try {
        this.erpCredentials = await this.get('/api/erp/credentials');
        if (!this.erpTypes.length) await this.loadERPTypes();
      } catch(e) { this.erpCredentials = []; }
    },
    openERPSetup(erp) {
      this.erpSetupType = erp;
      const existing = this.erpCredentials.find(c => c.erp_type === erp.type);
      this.erpSetupForm = { label: existing?.label || erp.name, endpoint_url: existing?.endpoint_url || '', credentials: {} };
      this.showERPSetupModal = true;
    },
    async saveERPCredential() {
      if (!this.erpSetupType) return;
      try {
        await this.post('/api/erp/credentials', {
          erp_type: this.erpSetupType.type,
          label: this.erpSetupForm.label,
          endpoint_url: this.erpSetupForm.endpoint_url,
          credentials: this.erpSetupForm.credentials,
        });
        this.showERPSetupModal = false;
        await this.loadERPCredentials();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async testERPConnection(credId) {
      this.erpTesting = credId;
      try {
        const r = await this.post(`/api/erp/credentials/${credId}/test`, {});
        alert(r.message);
        await this.loadERPCredentials();
      } catch(e) { alert(e.message||'Test failed'); }
      finally { this.erpTesting = null; }
    },
    async syncERPInvoices(credId) {
      const pid = this.currentProject?.id;
      try {
        const r = await this.post(`/api/erp/credentials/${credId}/sync/invoices`, { project_id: pid });
        alert(r.message);
        await this.loadERPCredentials();
      } catch(e) { alert(e.message||'Sync failed'); }
    },
    async deleteERPCredential(id) {
      if (!confirm('Remove this ERP integration?')) return;
      try { await this.delete(`/api/erp/credentials/${id}`); await this.loadERPCredentials(); } catch(e) {}
    },

    // ── AI Schedule Generation ────────────────────────────────────────
    async generateSchedule(file) {
      if (!file || !this.currentProject) return;
      this.aiSchedLoading = true;
      this.generatedSchedule = null;
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await fetch(`/api/project/${this.currentProject.id}/generate-schedule`, {
          method: 'POST', headers: { Authorization: 'Bearer ' + this.token }, body: fd
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Generation failed');
        this.generatedSchedule = data;
      } catch(e) { alert(e.message||'Schedule generation failed'); }
      finally { this.aiSchedLoading = false; }
    },
    async importSchedule() {
      if (!this.generatedSchedule || !this.currentProject) return;
      try {
        const r = await this.post(`/api/project/${this.currentProject.id}/generate-schedule/import`, { tasks: this.generatedSchedule.tasks });
        alert(`✓ Imported ${r.imported} tasks into your project. Go to Tasks to review and adjust.`);
        this.generatedSchedule = null;
        this.view = 'pm-tasks';
        await this.loadPMTasks();
      } catch(e) { alert(e.message||'Import failed'); }
    },

    // ── ERP Exports ──────────────────────────────────────────────────
    downloadExport(format) {
      const pid = this.currentProject ? `?project_id=${this.currentProject.id}` : '';
      const url = `/api/compliance/export/${format}${pid}`;
      const a = document.createElement('a'); a.href = url; a.download = '';
      a.style.display = 'none'; document.body.appendChild(a); a.click(); document.body.removeChild(a);
    },

    // ── Notifications ────────────────────────────────────────────────
    async loadNotifications() {
      this.notifLoading = true;
      try { this.notifData = await this.get('/api/notifications'); } catch(e) { this.notifData = null; }
      finally { this.notifLoading = false; }
    },

    // ── Equipment ────────────────────────────────────────────────────
    async loadEquipment() {
      this.equipLoading = true;
      try { this.equipList = await this.get('/api/equipment'); } catch(e) { this.equipList = []; }
      finally { this.equipLoading = false; }
    },
    async loadEquipmentUtilization() {
      try { this.equipUtilization = await this.get('/api/equipment/utilization-report'); } catch(e) {}
    },
    editEquip(e) {
      this.equipEditId = e.id;
      this.equipForm = { name:e.name, equipment_type:e.equipment_type||'', make:e.make||'', model:e.model||'', year:e.year||'', ownership:e.ownership, daily_rate:e.daily_rate||'', hourly_rate:e.hourly_rate||'', status:e.status, notes:e.notes||'' };
      this.showEquipModal = true;
    },
    async saveEquip() {
      try {
        if (this.equipEditId) await this.put(`/api/equipment/${this.equipEditId}`, this.equipForm);
        else await this.post('/api/equipment', this.equipForm);
        this.showEquipModal = false; this.equipEditId = null;
        await this.loadEquipment();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteEquip(id) {
      if (!confirm('Delete this equipment?')) return;
      try { await this.delete(`/api/equipment/${id}`); await this.loadEquipment(); } catch(e) {}
    },
    async openEquipLogs(e) {
      this.activeEquip = e;
      this.equipLogForm = { log_date:'', log_type:'usage', hours_used:0, fuel_litres:'', operator_name:'', work_description:'', cost:'', notes:'' };
      try { this.equipLogs = await this.get(`/api/equipment/${e.id}/logs`); } catch(e) { this.equipLogs = []; }
      this.showEquipLogModal = true;
    },
    async saveEquipLog() {
      if (!this.activeEquip) return;
      try {
        await this.post(`/api/equipment/${this.activeEquip.id}/logs`, this.equipLogForm);
        this.equipLogs = await this.get(`/api/equipment/${this.activeEquip.id}/logs`);
        this.equipLogForm = { log_date:'', log_type:'usage', hours_used:0, fuel_litres:'', operator_name:'', work_description:'', cost:'', notes:'' };
        await this.loadEquipment();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteEquipLog(id) {
      if (!this.activeEquip) return;
      try { await this.delete(`/api/equipment/${this.activeEquip.id}/logs/${id}`); this.equipLogs = await this.get(`/api/equipment/${this.activeEquip.id}/logs`); } catch(e) {}
    },

    // ── Lien Releases ────────────────────────────────────────────────
    async loadLienReleases() {
      if (!this.currentProject) return;
      this.lienReleasesLoading = true;
      try {
        const [releases, summary] = await Promise.all([
          this.get(`/api/project/${this.currentProject.id}/lien-releases`),
          this.get(`/api/project/${this.currentProject.id}/lien-releases/summary`),
        ]);
        this.lienReleases = releases; this.lienSummary = summary;
      } catch(e) { this.lienReleases = []; }
      finally { this.lienReleasesLoading = false; }
    },
    editLienRelease(r) {
      this.lienReleaseEditId = r.id;
      this.lienReleaseForm = { release_type:r.release_type, vendor_name:r.vendor_name||'', holdback_amount:r.holdback_amount||'', last_supply_date:'', lien_expiry_date:r.lien_expiry_date||'', status:r.status, statutory_declaration_received:r.statutory_declaration_received, notes:r.notes||'' };
      this.showLienReleaseModal = true;
    },
    async saveLienRelease() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.lienReleaseEditId) await this.put(`/api/project/${pid}/lien-releases/${this.lienReleaseEditId}`, this.lienReleaseForm);
        else await this.post(`/api/project/${pid}/lien-releases`, this.lienReleaseForm);
        this.showLienReleaseModal = false; this.lienReleaseEditId = null;
        await this.loadLienReleases();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteLienRelease(id) {
      if (!confirm('Delete this release record?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/lien-releases/${id}`); await this.loadLienReleases(); } catch(e) {}
    },

    // ── Vendor Scorecard ─────────────────────────────────────────────
    async loadVendorScores() {
      if (!this.currentProject) return;
      this.vendorScoresLoading = true;
      try { this.vendorScores = await this.get(`/api/project/${this.currentProject.id}/vendor-scores`); } catch(e) { this.vendorScores = []; }
      finally { this.vendorScoresLoading = false; }
    },
    editVendorScore(s) {
      this.vendorScoreEditId = s.id;
      this.vendorScoreForm = { vendor_name:s.vendor_name, period:s.period||'', quality:s.quality, timeliness:s.timeliness, safety:s.safety, communication:s.communication, value:s.value, would_rehire:s.would_rehire, comments:s.comments||'' };
      this.showVendorScoreModal = true;
    },
    async saveVendorScore() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.vendorScoreEditId) await this.put(`/api/project/${pid}/vendor-scores/${this.vendorScoreEditId}`, this.vendorScoreForm);
        else await this.post(`/api/project/${pid}/vendor-scores`, this.vendorScoreForm);
        this.showVendorScoreModal = false; this.vendorScoreEditId = null;
        await this.loadVendorScores();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteVendorScore(id) {
      if (!confirm('Delete this score?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/vendor-scores/${id}`); await this.loadVendorScores(); } catch(e) {}
    },

    // ── Client Selections ────────────────────────────────────────────
    async loadSelections() {
      if (!this.currentProject) return;
      this.selectionsLoading = true;
      try {
        const [items, summary] = await Promise.all([
          this.get(`/api/project/${this.currentProject.id}/selections`),
          this.get(`/api/project/${this.currentProject.id}/selections/summary`),
        ]);
        this.selectionItems = items; this.selSummary = summary;
      } catch(e) { this.selectionItems = []; }
      finally { this.selectionsLoading = false; }
    },
    async loadSelTokens() {
      if (!this.currentProject) return;
      try { this.selTokens = await this.get(`/api/project/${this.currentProject.id}/selections/tokens`); } catch(e) { this.selTokens = []; }
      if (!this.selTokens.length) {
        if (confirm('Create a client portal link for this project?')) {
          const name = prompt('Client name (optional):') || '';
          try {
            await this.post(`/api/project/${this.currentProject.id}/selections/tokens`, { client_name: name });
            await this.loadSelTokens();
          } catch(e) {}
        }
      }
    },
    editSelection(s) {
      this.selEditId = s.id;
      this.selForm = { item_name:s.item_name, category_id:s.category_id||'', standard_option:s.standard_option||'', client_choice:s.client_choice||'', allowance_amount:s.allowance_amount||'', actual_cost:s.actual_cost||'', upgrade_amount:s.upgrade_amount||'', status:s.status, due_date:s.due_date||'', notes:s.notes||'' };
      this.showSelModal = true;
    },
    async saveSelection() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.selEditId) await this.put(`/api/project/${pid}/selections/${this.selEditId}`, this.selForm);
        else await this.post(`/api/project/${pid}/selections`, this.selForm);
        this.showSelModal = false; this.selEditId = null;
        await this.loadSelections();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteSelection(id) {
      if (!confirm('Delete this selection item?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/selections/${id}`); await this.loadSelections(); } catch(e) {}
    },

    // ═══════════════ BANK FEED FUNCTIONS ════════════════════════════════════════

    async loadBankFeedConnections() {
      try {
        const data = await this.get('/api/bank-feed/connections');
        this.bankFeedConnections = data.connections || data || [];
        this.bankFeedUnmatched = (data.connections||data||[]).reduce((s,c) => s + (c.unmatched_count||0), 0);
        if (this.bankFeedConnections.length > 0 && this.view === 'bank-feed') {
          await this.loadBankFeedTransactions();
        }
      } catch(e) { this.bankFeedConnections = []; }
    },
    async loadBankFeedTransactions() {
      try {
        const data = await this.get(`/api/bank-feed/transactions?status=${this.bankFeedFilter}&limit=100`);
        this.bankFeedTxns = data.transactions || data || [];
      } catch(e) { this.bankFeedTxns = []; }
    },
    openBankFeedConnectModal() {
      this.bankFeedForm = { institution_name:'', account_name:'Operating Account', account_type:'chequing', masked_account:'', flinks_login_id:'' };
      this.showBankFeedModal = true;
    },
    async saveBankFeedConnection() {
      try {
        await this.post('/api/bank-feed/connections', { ...this.bankFeedForm, provider: this.bankFeedForm.flinks_login_id ? 'flinks' : 'manual' });
        this.showBankFeedModal = false;
        await this.loadBankFeedConnections();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async syncBankFeed(connectionId) {
      try {
        const result = await this.post(`/api/bank-feed/connections/${connectionId}/sync`, {});
        if (result.msg) alert(result.msg);
        await this.loadBankFeedConnections();
      } catch(e) { alert(e.message||'Sync failed'); }
    },
    async disconnectBankFeed(connectionId) {
      if (!confirm('Disconnect this bank account? Transaction history will be preserved.')) return;
      try { await this.delete(`/api/bank-feed/connections/${connectionId}`); await this.loadBankFeedConnections(); } catch(e) {}
    },
    async runAIMatch() {
      this.aiMatchLoading = true; this.aiMatchResult = null;
      try {
        this.aiMatchResult = await this.post('/api/bank-feed/ai-match-all', {});
        await this.loadBankFeedTransactions();
      } catch(e) { alert('AI matching failed: '+e.message); }
      this.aiMatchLoading = false;
    },
    async confirmBankTxn(id, txn) {
      try {
        const markPaid = txn.ai_invoice_id && confirm('Mark the linked invoice as paid?');
        await this.put(`/api/bank-feed/transactions/${id}/confirm`, {
          matched_invoice_id: txn.ai_invoice_id || null,
          mark_paid: markPaid,
        });
        await this.loadBankFeedTransactions();
      } catch(e) { alert(e.message||'Confirm failed'); }
    },
    async excludeBankTxn(id) {
      try { await this.put(`/api/bank-feed/transactions/${id}/exclude`, { notes: 'Excluded by user' }); await this.loadBankFeedTransactions(); } catch(e) {}
    },

    // ═══════════════ PHASE 11 FUNCTIONS ════════════════════════════════════════

    // ── QB Desktop IIF + Sage 50 CA Exports ──────────────────────────────────
    downloadQBIIF() {
      if (!this.currentProject) return alert('Select a project first');
      window.open(`/api/reports/export/qb-iif/${this.currentProject.id}?_t=${this.token}`, '_blank');
    },
    downloadSage50() {
      if (!this.currentProject) return alert('Select a project first');
      window.open(`/api/reports/export/sage50/${this.currentProject.id}?_t=${this.token}`, '_blank');
    },

    // ── Bank Statement Import ─────────────────────────────────────────────────
    async parseBankStatement() {
      if (!this.bankFile) return;
      this.bankParsing = true; this.bankDetected = null; this.bankMatches = [];
      try {
        const fd = new FormData(); fd.append('file', this.bankFile);
        const resp = await fetch('/api/bank-import/parse', { method:'POST', headers:{ Authorization:`Bearer ${this.token}` }, body:fd });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        this.bankDetected = data.bank_detected;
        this.bankTransactions = data.transactions || [];
        // Auto-match
        if (this.bankTransactions.length > 0) {
          const matchResp = await this.post('/api/bank-import/match', {
            transactions: this.bankTransactions,
            project_id: this.currentProject?.id || null,
          });
          this.bankMatches = matchResp.matches || [];
        }
      } catch(e) { alert('Parse failed: '+e.message); }
      this.bankParsing = false;
    },

    // ── FX / Multi-Currency ───────────────────────────────────────────────────
    async loadFXRates() {
      this.fxLoading = true;
      try { this.fxRates = await this.get('/api/fx/rates'); } catch(e) { this.fxRates = null; }
      this.fxLoading = false;
    },
    async convertFX() {
      try {
        this.fxResult = await this.post('/api/fx/convert', { amount: this.fxAmount, from_currency: this.fxFromCurrency });
      } catch(e) { alert('Conversion failed'); }
    },

    // ── Stress Testing ────────────────────────────────────────────────────────
    async runStressTest() {
      if (!this.currentProject) return alert('Select a project first');
      this.stressLoading = true; this.stressResults = null;
      try {
        this.stressResults = await this.post(`/api/project/${this.currentProject.id}/stress-test`, this.stressParams);
      } catch(e) { alert('Stress test failed: '+e.message); }
      this.stressLoading = false;
    },

    // ── AI CO Narrative (called from CO detail) ───────────────────────────────
    async generateCONarrative(coId) {
      if (!this.currentProject) return;
      const delayEvent = prompt('Describe the change event (e.g. "Owner issued ASI-14 adding 200 SF of additional concrete"):');
      if (!delayEvent) return;
      const timeDays = parseInt(prompt('Time impact (calendar days):', '0') || '0');
      const costAmount = parseFloat(prompt('Cost impact ($):', '0') || '0');
      try {
        const result = await this.post(`/api/project/${this.currentProject.id}/change-orders/${coId}/ai-narrative`, {
          delay_event: delayEvent, time_days: timeDays, cost_amount: costAmount
        });
        // Show in a modal or alert
        const win = window.open('', '_blank');
        if (win) {
          win.document.write(`<pre style="font-family:Georgia,serif;max-width:800px;margin:2rem auto;padding:2rem;line-height:1.6;white-space:pre-wrap">${result.narrative}</pre>`);
          win.document.close();
        }
      } catch(e) { alert('AI narrative failed: '+e.message); }
    },

    // ═══════════════ PHASE 11 MOBILE + GPS FUNCTIONS ══════════════════════════

    async captureGPSLocation() {
      if (!navigator.geolocation) { alert('Geolocation not supported on this device'); return; }
      this.gpsLoading = true; this.gpsLocation = null;
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.gpsCoords = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy };
          this.gpsLocation = `${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)} (±${Math.round(pos.coords.accuracy)}m)`;
          this.gpsLoading = false;
        },
        (err) => { alert('Location error: '+err.message); this.gpsLoading = false; },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
      );
    },
    async submitMobileTimecard() {
      if (!this.currentProject || !this.mobileTC.worker_name) return;
      this.mobileTCLoading = true; this.mobileTCSuccess = false;
      const payload = {
        ...this.mobileTC,
        location: this.gpsLocation || null,
        latitude: this.gpsCoords?.lat || null,
        longitude: this.gpsCoords?.lng || null,
        overtime_hours: 0, double_time_hours: 0,
      };
      try {
        await this.post(`/api/project/${this.currentProject.id}/timecards`, payload);
        this.mobileTCSuccess = true;
        this.mobileTC = { worker_name:this.mobileTC.worker_name, trade:this.mobileTC.trade, work_date:new Date().toISOString().slice(0,10), regular_hours:8, work_description:'' };
        this.gpsLocation = null; this.gpsCoords = null;
        setTimeout(() => { this.mobileTCSuccess = false; }, 4000);
      } catch(e) { alert(e.message||'Save failed'); }
      this.mobileTCLoading = false;
    },

    // ═══════════════ PHASE 10 FUNCTIONS ══════════════════════════════════════

    // ── QS / Inspector Reports ────────────────────────────────────────────────
    async loadQSReports() {
      if (!this.currentProject) return;
      try { this.qsReports = await this.get(`/api/project/${this.currentProject.id}/qs-reports`); } catch(e) { this.qsReports = []; }
    },
    openQSModal(r=null) {
      this.qsEditId = r?.id||null;
      this.qsForm = r ? { report_date:r.report_date||'', qs_firm:r.qs_firm||'', overall_pct_complete:r.overall_pct_complete||'', cost_to_complete:r.cost_to_complete||'', recommendation:r.recommendation||'approve', schedule_status:r.schedule_status||'on_track', schedule_delay_weeks:r.schedule_delay_weeks||'', deficiency_count:r.deficiency_count||0, deficiency_notes:r.deficiency_notes||'', notes:r.notes||'' }
              : { report_date:new Date().toISOString().slice(0,10), qs_firm:'', overall_pct_complete:'', cost_to_complete:'', recommendation:'approve', schedule_status:'on_track', schedule_delay_weeks:'', deficiency_count:0, deficiency_notes:'', notes:'' };
      this.showQSModal = true;
    },
    async saveQSReport() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.qsEditId) await this.put(`/api/project/${pid}/qs-reports/${this.qsEditId}`, this.qsForm);
        else await this.post(`/api/project/${pid}/qs-reports`, this.qsForm);
        this.showQSModal = false; this.qsEditId = null;
        await this.loadQSReports();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteQSReport(id) {
      if (!confirm('Delete this QS report?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/qs-reports/${id}`); await this.loadQSReports(); } catch(e) {}
    },
    async aiParseQSReport() {
      if (!this.qsAIFile || !this.currentProject) return;
      this.qsAIParsing = true;
      try {
        const fd = new FormData(); fd.append('file', this.qsAIFile);
        const resp = await fetch(`/api/project/${this.currentProject.id}/qs-reports/ai-parse`, { method:'POST', headers:{ Authorization:`Bearer ${this.token}` }, body:fd });
        if (!resp.ok) throw new Error(await resp.text());
        this.qsAIResult = await resp.json();
      } catch(e) { alert('AI parse failed: '+e.message); }
      this.qsAIParsing = false;
    },
    applyQSAIParsed() {
      if (!this.qsAIResult) return;
      const r = this.qsAIResult;
      this.qsForm = { report_date:r.report_date||new Date().toISOString().slice(0,10), qs_firm:r.qs_firm||'', overall_pct_complete:r.overall_pct_complete||'', cost_to_complete:r.cost_to_complete||'', recommendation:r.recommendation||'approve', schedule_status:r.schedule_status||'on_track', schedule_delay_weeks:r.schedule_delay_weeks||'', deficiency_count:r.deficiency_count||0, deficiency_notes:r.deficiency_notes||'', notes:'' };
      this.showQSAIParseModal = false; this.qsAIResult = null;
      this.showQSModal = true;
    },

    // ── Mezz Tranches ─────────────────────────────────────────────────────────
    async loadMezzTranches() {
      if (!this.currentProject) return;
      try { this.mezzData = await this.get(`/api/project/${this.currentProject.id}/mezz-tranches`); } catch(e) { this.mezzData = null; }
    },
    openMezzModal(t=null) {
      this.mezzEditId = t?.id||null;
      this.mezzForm = t ? { tranche_name:t.tranche_name, tranche_type:t.tranche_type||'senior', lender_name:t.lender_name||'', commitment_amount:t.commitment_amount||'', drawn_amount:t.drawn_amount||0, interest_rate:t.interest_rate||'', interest_type:t.interest_type||'fixed', priority_rank:t.priority_rank||1, maturity_date:t.maturity_date||'', draw_trigger:t.draw_trigger||'', notes:t.notes||'' }
                 : { tranche_name:'', tranche_type:'senior', lender_name:'', commitment_amount:'', drawn_amount:0, interest_rate:'', interest_type:'fixed', priority_rank:1, maturity_date:'', draw_trigger:'', notes:'' };
      this.showMezzModal = true;
    },
    async saveMezzTranche() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.mezzEditId) await this.put(`/api/project/${pid}/mezz-tranches/${this.mezzEditId}`, this.mezzForm);
        else await this.post(`/api/project/${pid}/mezz-tranches`, this.mezzForm);
        this.showMezzModal = false; this.mezzEditId = null;
        await this.loadMezzTranches();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteMezzTranche(id) {
      if (!confirm('Delete this tranche?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/mezz-tranches/${id}`); await this.loadMezzTranches(); } catch(e) {}
    },

    // ── CMHC Take-out ─────────────────────────────────────────────────────────
    async loadTakeoutConversion() {
      if (!this.currentProject) return;
      try { this.takeoutData = await this.get(`/api/project/${this.currentProject.id}/takeout-conversion`); } catch(e) { this.takeoutData = null; }
    },
    openTakeoutModal() {
      const t = this.takeoutData;
      this.takeoutForm = t ? { program:t.program||'CMHC MLI Select', permanent_lender:t.permanent_lender||'', permanent_loan_amount:t.permanent_loan_amount||'', permanent_rate:t.permanent_rate||'', amortization_years:t.amortization_years||'', expected_conversion_date:t.expected_conversion_date||'', target_occupancy_pct:t.target_occupancy_pct||'', dscr_at_stabilization:t.dscr_at_stabilization||'', status:t.status||'construction', notes:t.notes||'' }
                       : { program:'CMHC MLI Select', permanent_lender:'', permanent_loan_amount:'', permanent_rate:'', amortization_years:'', expected_conversion_date:'', target_occupancy_pct:'', dscr_at_stabilization:'', status:'construction', notes:'' };
      this.showTakeoutModal = true;
    },
    async saveTakeoutConversion() {
      if (!this.currentProject) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/takeout-conversion`, this.takeoutForm);
        this.showTakeoutModal = false;
        await this.loadTakeoutConversion();
      } catch(e) { alert(e.message||'Save failed'); }
    },

    // ── Loan Closing Checklist ────────────────────────────────────────────────
    async loadLoanClosingChecklist() {
      if (!this.currentProject) return;
      try {
        const data = await this.get(`/api/project/${this.currentProject.id}/loan-closing-checklist`);
        this.loanClosingItems = data.items||[]; this.loanClosingSummary = data.summary;
      } catch(e) { this.loanClosingItems = []; }
    },
    async seedLoanClosingChecklist() {
      if (!this.currentProject) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/loan-closing-checklist/seed`, {});
        await this.loadLoanClosingChecklist();
      } catch(e) { alert(e.message||'Seed failed'); }
    },
    openLoanClosingModal() {
      this.loanClosingForm = { category:'zoning', item_name:'', description:'', required_by:'', status:'outstanding', notes:'' };
      this.showLoanClosingModal = true;
    },
    async saveLoanClosingItem() {
      if (!this.currentProject) return;
      try {
        await this.post(`/api/project/${this.currentProject.id}/loan-closing-checklist`, this.loanClosingForm);
        this.showLoanClosingModal = false;
        await this.loadLoanClosingChecklist();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async toggleLoanClosingStatus(item) {
      const next = item.status === 'outstanding' ? 'received' : item.status === 'received' ? 'waived' : 'outstanding';
      await this.updateLoanClosingStatus(item, next);
    },
    async updateLoanClosingStatus(item, status) {
      if (!this.currentProject) return;
      try {
        await this.put(`/api/project/${this.currentProject.id}/loan-closing-checklist/${item.id}`, { status });
        item.status = status;
        await this.loadLoanClosingChecklist();
      } catch(e) {}
    },
    async deleteLoanClosingItem(id) {
      if (!confirm('Remove this checklist item?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/loan-closing-checklist/${id}`); await this.loadLoanClosingChecklist(); } catch(e) {}
    },

    // ── GST/HST Rebates ───────────────────────────────────────────────────────
    async loadGSTRebates() {
      if (!this.currentProject) return;
      try { this.gstRebates = await this.get(`/api/project/${this.currentProject.id}/gst-rebates`); } catch(e) { this.gstRebates = []; }
    },
    async calculateGSTRebate() {
      try {
        this.gstCalcResult = await this.post('/api/tax/calculate-rebate', this.gstCalc);
      } catch(e) { alert('Calculation failed'); }
    },
    openGSTModal(r=null) {
      this.gstEditId = r?.id||null;
      this.gstForm = r ? { rebate_type:r.rebate_type||'new_housing', province:r.province||'ON', applicant_name:r.applicant_name||'', unit_address:r.unit_address||'', purchase_price:r.purchase_price||'', gst_paid:r.gst_paid||'', status:r.status||'calculating', refund_amount:r.refund_amount||'' }
                      : { rebate_type:'new_housing', province:'ON', applicant_name:'', unit_address:'', purchase_price:'', gst_paid:'', status:'calculating', refund_amount:'' };
      this.showGSTModal = true;
    },
    async saveGSTRebate() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        if (this.gstEditId) await this.put(`/api/project/${pid}/gst-rebates/${this.gstEditId}`, this.gstForm);
        else await this.post(`/api/project/${pid}/gst-rebates`, this.gstForm);
        this.showGSTModal = false; this.gstEditId = null;
        await this.loadGSTRebates();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteGSTRebate(id) {
      if (!confirm('Delete this rebate application?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/gst-rebates/${id}`); await this.loadGSTRebates(); } catch(e) {}
    },

    // ── EFT Batches ───────────────────────────────────────────────────────────
    async loadEFTBatches() {
      try { this.eftBatches = await this.get('/api/eft-batches'); } catch(e) { this.eftBatches = []; }
    },
    openEFTModal() {
      this.eftForm = { batch_number:'EFT-'+(this.eftBatches.length+1).toString().padStart(3,'0'), value_date:new Date().toISOString().slice(0,10), bank_name:'', originator_id:'', notes:'' };
      this.showEFTModal = true;
    },
    async saveEFTBatch() {
      try {
        await this.post('/api/eft-batches', this.eftForm);
        this.showEFTModal = false;
        await this.loadEFTBatches();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    downloadEFTFile(batchId) {
      window.open(`/api/eft-batches/${batchId}/download?token=${encodeURIComponent(this.token)}`, '_blank');
    },
    async deleteEFTBatch(id) {
      if (!confirm('Delete this draft batch?')) return;
      try { await this.delete(`/api/eft-batches/${id}`); await this.loadEFTBatches(); } catch(e) {}
    },

    // ── API Keys ──────────────────────────────────────────────────────────────
    async loadAPIKeys() {
      try { this.apiKeys = await this.get('/api/api-keys'); } catch(e) { this.apiKeys = []; }
    },
    async createAPIKey() {
      const name = prompt('API key name (e.g. Zapier Integration):');
      if (!name) return;
      const scopes = prompt('Scopes (read / write / admin):', 'read') || 'read';
      try {
        const result = await this.post('/api/api-keys', { name, scopes });
        this.newAPIKey = result.key;
        await this.loadAPIKeys();
      } catch(e) { alert(e.message||'Failed'); }
    },
    async toggleAPIKey(id) {
      try { await this.put(`/api/api-keys/${id}/toggle`, {}); await this.loadAPIKeys(); } catch(e) {}
    },
    async deleteAPIKey(id) {
      if (!confirm('Permanently revoke and delete this API key?')) return;
      try { await this.delete(`/api/api-keys/${id}`); await this.loadAPIKeys(); } catch(e) {}
    },

    // ── Webhooks ──────────────────────────────────────────────────────────────
    async loadWebhooks() {
      try { this.webhooks = await this.get('/api/webhooks'); } catch(e) { this.webhooks = []; }
    },
    openWebhookModal() {
      this.webhookForm = { name:'', url:'', events:'invoice.created' };
      this.showWebhookModal = true;
    },
    async saveWebhook() {
      try {
        const result = await this.post('/api/webhooks', this.webhookForm);
        this.newWebhookSecret = result.signing_secret;
        this.showWebhookModal = false;
        await this.loadWebhooks();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async testWebhook(id) {
      try {
        const r = await this.post(`/api/webhooks/${id}/test`, {});
        alert(r.success ? `✓ Webhook responded with HTTP ${r.http_status} in ${r.duration_ms}ms` : `✗ Webhook failed: HTTP ${r.http_status}`);
      } catch(e) { alert('Test failed: '+e.message); }
    },
    async deleteWebhook(id) {
      if (!confirm('Delete this webhook?')) return;
      try { await this.delete(`/api/webhooks/${id}`); await this.loadWebhooks(); } catch(e) {}
    },

    // ── Adjudication Cases ────────────────────────────────────────────────────
    async loadAdjudications() {
      if (!this.currentProject) return;
      try { this.adjudications = await this.get(`/api/project/${this.currentProject.id}/adjudications`); } catch(e) { this.adjudications = []; }
    },
    openAdjModal(c=null) {
      this.adjEditId = c?.id||null;
      this.adjForm = c ? { case_number:c.case_number||'', province:c.province||'ON', claimant_name:c.claimant_name||'', respondent_name:c.respondent_name||'', disputed_amount:c.disputed_amount||'', status:c.status||'initiated', adjudicator_name:c.adjudicator_name||'', adjudicator_appointed_date:c.adjudicator_appointed_date||'', description:c.description||'' }
                   : { case_number:'', province:'ON', claimant_name:'', respondent_name:'', disputed_amount:'', status:'initiated', adjudicator_name:'', adjudicator_appointed_date:'', description:'' };
      this.showAdjModal = true;
    },
    async saveAdjudication() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        const result = this.adjEditId
          ? await this.put(`/api/project/${pid}/adjudications/${this.adjEditId}`, this.adjForm)
          : await this.post(`/api/project/${pid}/adjudications`, this.adjForm);
        this.showAdjModal = false; this.adjEditId = null;
        if (result.determination_deadline) alert(`Determination deadline set: ${result.determination_deadline}`);
        await this.loadAdjudications();
      } catch(e) { alert(e.message||'Save failed'); }
    },
    async deleteAdjudication(id) {
      if (!confirm('Delete this adjudication case?')) return;
      try { await this.delete(`/api/project/${this.currentProject.id}/adjudications/${id}`); await this.loadAdjudications(); } catch(e) {}
    },

    // ── AI Document Q&A ───────────────────────────────────────────────────────
    async askDocQA() {
      if (!this.currentProject || !this.docQAQuestion.trim()) return;
      this.docQALoading = true; this.docQAAnswer = null; this.docQASources = [];
      try {
        const result = await this.post(`/api/project/${this.currentProject.id}/doc-qa`, { question: this.docQAQuestion });
        this.docQAAnswer = result.answer;
        this.docQASources = result.sources_searched||[];
      } catch(e) { this.docQAAnswer = 'Error: '+e.message; }
      this.docQALoading = false;
    },

    // ── AI Client Update Generator ────────────────────────────────────────────
    async generateClientUpdate() {
      if (!this.currentProject) return;
      this.clientUpdateLoading = true; this.clientUpdateText = null;
      try {
        const result = await this.post(`/api/project/${this.currentProject.id}/ai-client-update`, { tone: this.clientUpdateTone });
        this.clientUpdateText = result.update;
        this.clientUpdateMeta = result;
      } catch(e) { alert('Generation failed: '+e.message); }
      this.clientUpdateLoading = false;
    },
    async copyClientUpdate() {
      if (!this.clientUpdateText) return;
      try { await navigator.clipboard.writeText(this.clientUpdateText); alert('Copied to clipboard!'); } catch(e) {}
    },

    // ═══════════════ EXECUTION FORECAST ════════════════════════════════════════

    async loadExecutionForecast() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      try {
        const [sds, periods] = await Promise.all([
          this.get(`/api/project/${pid}/execution/subdivisions`),
          this.get(`/api/project/${pid}/execution/periods`),
        ]);
        this.efSDs = sds || [];
        this.efPeriods = periods || [];
        if (this.efTab === 'grid') await this.loadEFGrid();
        if (this.efTab === 'summary') await this.loadEFSummary();
        if (this.efTab === 'actuals') await this.loadEFActualsForm();
      } catch(e) { console.error('EF load error', e); }
    },

    async loadEFGrid() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      let url = `/api/project/${pid}/execution/grid`;
      const qs = [];
      if (this.efFilterSD) qs.push(`sd_code=${encodeURIComponent(this.efFilterSD)}`);
      if (qs.length) url += '?' + qs.join('&');
      try {
        const data = await this.get(url);
        this.efGrid = data.tasks || [];
        this.efPeriods = data.periods || [];
      } catch(e) { this.efGrid = []; }
    },

    async loadEFSummary() {
      if (!this.currentProject) return;
      const pid = this.currentProject.id;
      let url = `/api/project/${pid}/execution/summary`;
      if (this.efFilterSD) url += `?sd_code=${encodeURIComponent(this.efFilterSD)}`;
      try {
        const data = await this.get(url);
        this.efSummary = data.workstreams || [];
        this.efSummaryPeriods = data.periods || [];
      } catch(e) { this.efSummary = []; }
    },

    async loadEFActualsForm() {
      if (!this.currentProject || !this.efActualsPeriod) return;
      const pid = this.currentProject.id;
      let url = `/api/project/${pid}/execution/grid`;
      if (this.efFilterSD) url += `?sd_code=${encodeURIComponent(this.efFilterSD)}`;
      try {
        const data = await this.get(url);
        this.efActualsEntries = (data.tasks || []).map(t => ({
          task_id: t.task_id,
          node_code: t.node_code,
          sd_code: t.sd_code,
          workstream: t.workstream,
          unit: t.unit,
          vendor: t.vendor,
          planned: (t.periods[this.efActualsPeriod] || {}).plan || 0,
          actual: (t.periods[this.efActualsPeriod] || {}).actual ?? '',
          notes: '',
        }));
      } catch(e) { this.efActualsEntries = []; }
    },

    async switchEFTab(tab) {
      this.efTab = tab;
      if (tab === 'grid') await this.loadEFGrid();
      if (tab === 'summary') await this.loadEFSummary();
      if (tab === 'actuals' && this.efActualsPeriod) await this.loadEFActualsForm();
    },

    async importEFExcel() {
      if (!this.efImportFile || !this.currentProject) return;
      this.efImporting = true; this.efImportResult = null;
      try {
        const fd = new FormData();
        fd.append('file', this.efImportFile);
        const resp = await fetch(`/api/project/${this.currentProject.id}/execution/import`, {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + this.token,
                     'X-Organization-Id': String(this.activeOrgId || '') },
          body: fd,
        });
        if (!resp.ok) { const e = await resp.json(); throw new Error(e.detail || 'Import failed'); }
        this.efImportResult = await resp.json();
        await this.loadExecutionForecast();
        this.efTab = 'grid';
      } catch(e) { alert('Import error: ' + e.message); }
      this.efImporting = false;
    },

    async clearEFData() {
      if (!this.currentProject) return;
      if (!confirm('Clear ALL execution forecast data for this project? This cannot be undone.')) return;
      await this.delete(`/api/project/${this.currentProject.id}/execution/clear`);
      this.efGrid = []; this.efSummary = []; this.efPeriods = []; this.efSDs = [];
      this.efImportResult = null;
    },

    async saveEFActuals() {
      if (!this.currentProject || !this.efActualsPeriod) return;
      this.efActualsSaving = true;
      const entries = this.efActualsEntries
        .filter(e => e.actual !== '' && e.actual !== null)
        .map(e => ({ task_id: e.task_id, actual_qty: parseFloat(e.actual) || 0, notes: e.notes }));
      try {
        const r = await this.post(`/api/project/${this.currentProject.id}/execution/actuals`, {
          period: this.efActualsPeriod, entries,
        });
        alert(r.msg || 'Saved');
        await this.loadEFGrid();
      } catch(e) { alert('Save failed: ' + e.message); }
      this.efActualsSaving = false;
    },

    downloadEFExcel() {
      if (!this.currentProject) return;
      window.open(`/api/project/${this.currentProject.id}/execution/export?_t=${this.token}`, '_blank');
    },

    efVariance(planned, actual) {
      if (actual === null || actual === undefined || actual === '') return '—';
      const v = parseFloat(actual) - parseFloat(planned || 0);
      return (v >= 0 ? '+' : '') + v.toFixed(1);
    },

    efPct(planned, actual) {
      if (!planned || planned == 0 || actual === null || actual === undefined || actual === '') return '—';
      return Math.round((parseFloat(actual) / parseFloat(planned)) * 100) + '%';
    },

  };
}
