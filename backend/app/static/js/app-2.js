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
      // Handle deep-link routes: /reset-password, /signup, /accept-invite
      const path = window.location.pathname.replace(/^\//, '');
      if (path === 'reset-password') { this.resetToken = new URLSearchParams(window.location.search).get('token') || ''; this.view = 'reset-password'; return; }
      if (path === 'signup') { this.view = 'signup'; return; }
      if (path === 'accept-invite') { this.inviteToken = new URLSearchParams(window.location.search).get('token') || ''; this.view = 'accept-invite'; return; }

      const saved = localStorage.getItem('invoice_token');
      const savedUser = localStorage.getItem('invoice_user');
      if (saved && savedUser) {
        this.token = saved;
        this.user = JSON.parse(savedUser);
        // Restore org context — fetch fresh from server to get membership list
        try {
          this.orgs = await this.get('/api/org');
          const savedOrgId = parseInt(localStorage.getItem('currentOrgId'));
          this.currentOrg = (savedOrgId && this.orgs.find(o => o.id === savedOrgId)) || this.orgs[0] || null;
        } catch(e) { this.orgs = []; }
        this.view = 'dashboard';
        await this.loadProjects();
        await Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()]);
        if (this.user?.is_admin) await this.loadApiKeys();
      }
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
      this.view = 'dashboard';
      this.loadProjects().then(() => {
        Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()])
          .then(() => { if (this.user?.is_admin) this.loadApiKeys(); });
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
      this.token = null; this.user = null;
      this.orgs = []; this.currentOrg = null;
      localStorage.removeItem('invoice_token');
      localStorage.removeItem('invoice_user');
      localStorage.removeItem('currentOrgId');
      if (this.sseSource) this.sseSource.close();
      this.view = 'landing';
    },

    // ── Org management ────────────────────────────────────────────
    async loadOrgMembers() {
      try { this.orgMembers = await this.get('/api/org/members'); } catch(e) {}
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
        this.setAuth(data);
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

    async loadStats() {
      try { this.stats = await this.get('/api/invoices/stats'); } catch (e) {}
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
      { key: 'tax_rate', label: 'Tax %', active: true, visible: true, exportable: true },
      { key: 'line_total', label: 'Line Total', active: true, visible: true, exportable: true },
      { key: 'manufacturer', label: 'Manufacturer', active: false, visible: false, exportable: true },
      { key: 'sub_division', label: 'Sub-Division', active: true, visible: true, exportable: true },
    ],
    get visibleLineItemCols() { return this.lineItemColumns.filter(c => c.active !== false && c.visible); },
    toggleLineItemCol(col, field) {
      col[field] = !col[field];
      localStorage.setItem('lineItemColumns', JSON.stringify(this.lineItemColumns));
    },

    get lineItemsFlat() {
      const rows = [];
      for (const inv of this.invoices) {
        const items = inv.extracted_data?.line_items;
        if (Array.isArray(items) && items.length > 0) {
          for (const item of items) {
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
    createUserForm: { username: '', email: '', password: '', is_admin: false },
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
        await this.post('/api/admin/users', this.createUserForm);
        this.showCreateUserModal = false;
        this.createUserForm = { username: '', email: '', password: '', is_admin: false };
        await this.loadUsers();
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

    // ── PM helpers ────────────────────────────────────────────────
    get canAccessPM() {
      const pm = ['owner','admin','pm_admin','site_supervisor','vendor_pm','finance_admin','editor','viewer','pm_viewer'];
      return pm.includes(this.currentOrg?.role);
    },
    get canAccessFinance() {
      const f = ['owner','admin','finance_admin','finance_viewer','editor','viewer'];
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
  };
}
