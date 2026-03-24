const API = '';  // same origin

function app() {
  return {
    // ── Auth ──────────────────────────────────────────────────────
    view: 'login',
    authTab: 'login',
    authLoading: false,
    authError: '',
    loginForm: { username: '', password: '' },
    regForm: { username: '', email: '', password: '' },
    user: null,
    token: null,

    // ── Invoices ──────────────────────────────────────────────────
    invoices: [],
    stats: {},
    filters: { start_date: '', end_date: '', vendor: '', currency: '', status: '' },
    exportDates: { start: '', end: '' },
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
    costCategories: [],
    subdivisions: [],
    selectedAllocInvoice: null,
    allocations: [],
    allocForm: { category_id: '', sub_category_id: '', subdivision_id: '', percentage: 100 },
    showAllocModal: false,
    showPaymentModal: false,
    paymentForm: { invoice_id: null, amount: '', payment_date: '', method: '', reference: '', notes: '' },
    invoicePayments: [],

    // ── Init ──────────────────────────────────────────────────────
    async init() {
      const saved = localStorage.getItem('invoice_token');
      const savedUser = localStorage.getItem('invoice_user');
      if (saved && savedUser) {
        this.token = saved;
        this.user = JSON.parse(savedUser);
        this.view = 'dashboard';
        await Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions()]);
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
      Promise.all([this.loadInvoices(), this.loadColumns(), this.loadStats(), this.loadCategories(), this.loadProjectDashboard(), this.loadSubdivisions()])
        .then(() => { if (this.user?.is_admin) this.loadApiKeys(); });
    },

    logout() {
      this.token = null;
      this.user = null;
      localStorage.removeItem('invoice_token');
      localStorage.removeItem('invoice_user');
      if (this.sseSource) this.sseSource.close();
      this.view = 'login';
    },


    // ── Invoices ──────────────────────────────────────────────────
    async loadInvoices() {
      const params = new URLSearchParams({ page: this.pagination.page, limit: this.pagination.limit });
      if (this.filters.start_date) params.set('start_date', this.filters.start_date);
      if (this.filters.end_date)   params.set('end_date',   this.filters.end_date);
      if (this.filters.vendor)     params.set('vendor',     this.filters.vendor);
      if (this.filters.currency)   params.set('currency',   this.filters.currency);
      if (this.filters.status)     params.set('status',     this.filters.status);

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
      this.filters = { start_date: '', end_date: '', vendor: '', currency: '', status: '' };
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

        // Add to processing queue
        data.results.filter(r => r.status === 'queued').forEach(r => {
          this.processingQueue.push({ id: r.invoice_id, filename: r.filename, status: 'processing' });
        });

        // Start SSE listener
        this.startSSE();

        // Refresh table after short delay
        setTimeout(() => { this.loadInvoices(); this.loadStats(); }, 1500);
      } catch (e) {
        this.uploadError = e.message;
      } finally {
        this.uploadLoading = false;
      }
    },


    // ── SSE processing updates ────────────────────────────────────
    startSSE() {
      if (this.sseSource) this.sseSource.close();
      const url = `/api/invoices/stream?token=${encodeURIComponent(this.token)}`;
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
        this.projectDash = await this.get('/api/project/dashboard');
        this.costCategories = this.projectDash?.categories || [];
      } catch (e) { console.error(e); }
    },

    async loadSubdivisions() {
      try { this.subdivisions = await this.get('/api/project/subdivisions'); } catch (e) {}
    },

    async loadCostCategories() {
      try { this.costCategories = await this.get('/api/project/categories'); } catch (e) {}
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

    budgetHealth(remaining, budget) {
      if (!budget || budget <= 0) return 'text-gray-400';
      const pct = remaining / budget;
      if (pct > 0.2) return 'text-green-600';
      if (pct > 0) return 'text-amber-500';
      return 'text-red-600';
    },

    // ── Settings ──────────────────────────────────────────────────
    async saveSettings() {
      this.settingsSaved = true;
      setTimeout(() => this.settingsSaved = false, 5000);
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
