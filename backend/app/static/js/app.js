const API = '';  // same origin

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

    // ── Multi-project ──────────────────────────────────────────────
    projects: [],
    currentProject: null,
    showNewProjectModal: false,
    newProjectForm: { name: '', code: '', client: '', address: '', start_date: '', end_date: '', total_budget: 0, currency: 'CAD' },
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

    // ── Init ──────────────────────────────────────────────────────
    async init() {
      const saved = localStorage.getItem('invoice_token');
      const savedUser = localStorage.getItem('invoice_user');
      if (saved && savedUser) {
        this.token = saved;
        this.user = JSON.parse(savedUser);
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
      localStorage.setItem('invoice_token', this.token);
      localStorage.setItem('invoice_user', JSON.stringify(this.user));
      this.view = 'dashboard';
      this.loadProjects().then(() => {
        Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions(), this.loadPayroll(), this.loadUsers()])
          .then(() => { if (this.user?.is_admin) this.loadApiKeys(); });
      });
    },

    logout() {
      this.token = null;
      this.user = null;
      localStorage.removeItem('invoice_token');
      localStorage.removeItem('invoice_user');
      if (this.sseSource) this.sseSource.close();
      this.view = 'landing';
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
      // Reload all project-scoped data
      Promise.all([
        this.loadProjectDashboard(),
        this.loadSubdivisions ? this.loadSubdivisions() : Promise.resolve(),
        this.loadPayroll(),
      ]);
    },

    get _pid() {
      return this.currentProject ? `?project_id=${this.currentProject.id}` : '';
    },

    async createProject() {
      if (!this.newProjectForm.name.trim()) {
        this.newProjectError = 'Project name is required.'; return;
      }
      this.newProjectLoading = true; this.newProjectError = '';
      try {
        const proj = await this.post('/api/project', this.newProjectForm);
        this.projects.push(proj);
        this.currentProject = proj;
        localStorage.setItem('currentProjectId', proj.id);
        this.showNewProjectModal = false;
        this.newProjectForm = { name: '', code: '', client: '', address: '', start_date: '', end_date: '', total_budget: 0, currency: 'CAD' };
        await this.loadProjectDashboard();
      } catch (e) {
        this.newProjectError = e.message || 'Failed to create project';
      } finally { this.newProjectLoading = false; }
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
      try { this.costCategories = await this.get(\); } catch (e) {}
    },

    async updateProjectBudget(field, value) {
      try { await this.put('/api/project', { [field]: value }); await this.loadProjectDashboard(); } catch (e) { alert(e.message); }
    },

    async updateCategoryBudget(catId, budget) {
      try { await this.put(`/api/project/categories/${catId}`, { budget: parseFloat(budget) }); await this.loadProjectDashboard(); } catch (e) { alert(e.message); }
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
      try { this.draws = await this.get(\); } catch (e) {}
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
          await this.post(\, this.drawForm);
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
      try { this.claims = await this.get(\); } catch (e) {}
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
          await this.post(\, this.claimForm);
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
          await this.post(\, this.payrollForm);
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
      return this.token ? { Authorization: `Bearer ${this.token}` } : {};
    },
  };
}
