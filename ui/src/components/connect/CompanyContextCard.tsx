import React, { useState, useRef, ChangeEvent, DragEvent } from 'react';
import {
  CompanyContextRecord,
  ExtractionResult,
  FieldProvenance,
  extractCompanyContext,
  scrapeCompanyWebsite,
  saveCompanyContext
} from '../../api';

export const INDUSTRIES = [
  'B2B SaaS',
  'B2C SaaS',
  'Enterprise Software',
  'Fintech',
  'Healthtech',
  'DevTools & Infrastructure',
  'AI & Machine Learning',
  'Cybersecurity',
  'E-commerce & Retail',
  'Edtech',
  'Other'
];

export const BUSINESS_MODELS = [
  'Subscription (SaaS)',
  'Usage-Based / Consumption',
  'Hybrid (Subscription + Usage)',
  'Freemium SaaS',
  'Marketplace Commission',
  'API / Transactional',
  'Enterprise License',
  'Other'
];

export const STAGES = [
  'Pre-Seed',
  'Seed',
  'Series A',
  'Series B',
  'Series C+',
  'Growth',
  'Bootstrapped',
  'Public'
];

interface UploadedFileItem {
  id: string;
  filename: string;
  size: number;
  content: string;
  status: 'ready' | 'extracting' | 'extracted' | 'error';
  errorMessage?: string;
}

interface CompanyContextCardProps {
  initialContext?: CompanyContextRecord | null;
  onContextSaved: (saved: CompanyContextRecord) => void;
}

export const CompanyContextCard: React.FC<CompanyContextCardProps> = ({
  initialContext,
  onContextSaved
}) => {
  // Form State
  const [formData, setFormData] = useState<{
    company_name: string;
    industry: string;
    business_model: string;
    description: string;
    products_services: string;
    target_customers: string;
    revenue_model: string;
    geographic_presence: string;
    stage: string;
    strategic_goals: string;
    major_challenges: string;
    key_competitors: string;
    website_url: string;
  }>({
    company_name: initialContext?.company_name || '',
    industry: initialContext?.industry || '',
    business_model: initialContext?.business_model || '',
    description: initialContext?.description || '',
    products_services: initialContext?.products_services || '',
    target_customers: initialContext?.target_customers || '',
    revenue_model: initialContext?.revenue_model || '',
    geographic_presence: initialContext?.geographic_presence || '',
    stage: initialContext?.stage || '',
    strategic_goals: initialContext?.strategic_goals || '',
    major_challenges: initialContext?.major_challenges || '',
    key_competitors: initialContext?.key_competitors || '',
    website_url: initialContext?.website_url || ''
  });

  // Provenance tracking for each field
  const [provenance, setProvenance] = useState<Record<string, FieldProvenance>>(
    initialContext?.provenance || {}
  );

  // Uploaded files list
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);

  // Website enrichment state
  const [websiteUrlInput, setWebsiteUrlInput] = useState(initialContext?.website_url || '');
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [scrapeSuccessMsg, setScrapeSuccessMsg] = useState<string | null>(null);

  // Markdown previews toggle state for long-text fields
  const [activePreviews, setActivePreviews] = useState<Record<string, boolean>>({});

  // Saving state & notices
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [extractionSummary, setExtractionSummary] = useState<{
    extractedCount: number;
    missingRequiredCount: number;
    sources: string[];
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Required fields validator
  const requiredFieldKeys = [
    'company_name',
    'industry',
    'business_model',
    'description',
    'products_services',
    'target_customers',
    'revenue_model',
    'stage',
    'strategic_goals'
  ];

  const getMissingRequiredFields = () => {
    return requiredFieldKeys.filter((key) => {
      const val = formData[key as keyof typeof formData];
      return !val || !val.trim();
    });
  };

  // Drag and drop handlers
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFiles(Array.from(e.target.files));
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const processFiles = async (files: File[]) => {
    const mdFiles = files.filter((f) => f.name.toLowerCase().endsWith('.md'));
    if (mdFiles.length === 0) {
      alert('Only Markdown (.md) documents are supported.');
      return;
    }

    const newItems: UploadedFileItem[] = [];
    for (const file of mdFiles) {
      try {
        const text = await file.text();
        newItems.push({
          id: `${file.name}_${Date.now()}_${newItems.length}`,
          filename: file.name,
          size: file.size,
          content: text,
          status: 'ready'
        });
      } catch (err: any) {
        console.error(`Failed reading file ${file.name}:`, err);
      }
    }

    setUploadedFiles((prev) => [...prev, ...newItems]);
  };

  const handleRemoveFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // AI-Powered Auto-Fill Execution
  const handleExtractAndAutoFill = async () => {
    if (uploadedFiles.length === 0) return;
    setIsExtracting(true);
    setSaveError(null);

    // Update statuses to extracting
    setUploadedFiles((prev) =>
      prev.map((f) => ({ ...f, status: 'extracting' }))
    );

    try {
      const payloadFiles = uploadedFiles.map((f) => ({
        filename: f.filename,
        content: f.content
      }));

      const result: ExtractionResult = await extractCompanyContext(payloadFiles);

      // Merge extracted fields into form without silently discarding existing manual inputs if desired
      setFormData((prev) => {
        const updated = { ...prev };
        let populatedCount = 0;
        for (const [key, val] of Object.entries(result.fields)) {
          if (val && val.trim()) {
            (updated as any)[key] = val;
            populatedCount += 1;
          }
        }
        return updated;
      });

      // Update provenance
      setProvenance((prev) => ({
        ...prev,
        ...result.provenance
      }));

      // Update files status to extracted
      setUploadedFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'extracted' }))
      );

      const missing = getMissingRequiredFields();
      setExtractionSummary({
        extractedCount: Object.keys(result.provenance).length,
        missingRequiredCount: result.missing_fields.length,
        sources: result.document_names
      });
    } catch (err: any) {
      console.error('Extraction error:', err);
      setSaveError(err.message || 'AI document extraction failed.');
      setUploadedFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'error', errorMessage: err.message }))
      );
    } finally {
      setIsExtracting(false);
    }
  };

  // Website Enrichment
  const handleEnrichFromWebsite = async () => {
    const rawUrl = (websiteUrlInput || formData.website_url).trim();
    if (!rawUrl) {
      setScrapeError('Please enter a valid website URL.');
      return;
    }

    setIsScraping(true);
    setScrapeError(null);
    setScrapeSuccessMsg(null);

    try {
      const result: ExtractionResult = await scrapeCompanyWebsite(rawUrl);

      // Rule: Never silently overwrite existing manual or uploaded information.
      // Only populate fields that are currently empty, or keep user in control.
      let enrichedFieldsCount = 0;
      setFormData((prev) => {
        const updated = { ...prev };
        if (!updated.website_url) updated.website_url = rawUrl;

        for (const [key, val] of Object.entries(result.fields)) {
          if (val && val.trim()) {
            const currentVal = (updated as any)[key];
            // If field is currently empty, auto-populate with scraped data
            if (!currentVal || !currentVal.trim()) {
              (updated as any)[key] = val;
              enrichedFieldsCount += 1;
            }
          }
        }
        return updated;
      });

      // Record provenance for newly enriched fields
      setProvenance((prev) => {
        const updatedProv = { ...prev };
        for (const [key, prov] of Object.entries(result.provenance)) {
          if (!updatedProv[key] || !updatedProv[key].extracted) {
            updatedProv[key] = prov;
          }
        }
        return updatedProv;
      });

      setScrapeSuccessMsg(
        enrichedFieldsCount > 0
          ? `Enriched ${enrichedFieldsCount} fields from ${rawUrl}. Existing manual fields were preserved.`
          : `Website scraped successfully. All current fields already contain data.`
      );
    } catch (err: any) {
      console.error('Website scraping failed:', err);
      setScrapeError(err.message || 'Failed to scrape website.');
    } finally {
      setIsScraping(false);
    }
  };

  // Field change handler
  const handleFieldChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    // Mark as manual edit in provenance
    setProvenance((prev) => ({
      ...prev,
      [key]: {
        source: 'manual',
        source_detail: 'User edit',
        confidence: 1.0,
        extracted: false
      }
    }));
  };

  // Toggle Markdown preview for long text fields
  const togglePreview = (fieldName: string) => {
    setActivePreviews((prev) => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  };

  // Save company context
  const handleSave = async () => {
    setSaveError(null);
    setSaveSuccessMsg(null);

    const missing = getMissingRequiredFields();
    if (missing.length > 0) {
      setSaveError(
        `Please complete required fields before saving: ${missing
          .map((f) => f.replace(/_/g, ' '))
          .join(', ')}`
      );
      return;
    }

    setIsSaving(true);
    try {
      const payload: Partial<CompanyContextRecord> = {
        ...formData,
        provenance,
        uploaded_documents: uploadedFiles.map((f) => ({
          filename: f.filename,
          size: f.size,
          uploaded_at: new Date().toISOString()
        }))
      };

      const res = await saveCompanyContext(payload);
      setSaveSuccessMsg('Company Context saved and active. Executive agents are now grounded with your context.');
      onContextSaved(res.context);
    } catch (err: any) {
      console.error('Failed to save company context:', err);
      setSaveError(err.message || 'Failed to save company context.');
    } finally {
      setIsSaving(false);
    }
  };

  const missingFieldsList = getMissingRequiredFields();

  return (
    <div className="bg-[#181818] border border-[#2e2e2e] rounded-2xl p-6 shadow-xl space-y-6">
      {/* Card Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-[#282828]">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-sm shadow-purple-500/50" />
            <h2 className="text-lg font-bold text-white tracking-tight">Company Context</h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-purple-500/15 text-purple-300 border border-purple-500/30">
              Foundational Integration #1
            </span>
          </div>
          <p className="text-xs text-[#888888] mt-1">
            Establish ground-truth strategic, product, and business architecture. Ground executive agents before operational telemetry ingestion.
          </p>
        </div>

        {initialContext?.updated_at && (
          <div className="text-[11px] font-mono text-[#777777] bg-[#141414] px-3 py-1.5 rounded-lg border border-[#282828] self-start sm:self-auto">
            Last Synced: {new Date(initialContext.updated_at).toLocaleDateString()}
          </div>
        )}
      </div>

      {/* Part A: Markdown Document Upload */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-[#cccccc] flex items-center gap-2">
            <span>A. Upload Markdown Documents</span>
            <span className="text-[10px] text-[#666666] font-normal">(Optional · Multi-document support)</span>
          </label>
          <span className="text-[11px] text-[#888888]">Accepts .md only</span>
        </div>

        {/* Drag and Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2 ${
            isDragging
              ? 'border-purple-500 bg-purple-500/10'
              : 'border-[#333333] hover:border-[#444444] bg-[#141414]'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".md"
            multiple
            className="hidden"
          />
          <div className="w-10 h-10 rounded-full bg-[#1e1e1e] border border-[#2e2e2e] flex items-center justify-center text-purple-400 text-lg">
            📄
          </div>
          <div className="text-xs text-[#d4d4d4] font-medium">
            Drag & drop company <span className="text-purple-400 font-mono">.md</span> files here, or{' '}
            <span className="text-purple-400 underline underline-offset-2 hover:text-purple-300">browse files</span>
          </div>
          <div className="text-[11px] text-[#666666]">
            Upload pitch decks, executive summaries, product briefs, or strategy notes in Markdown.
          </div>
        </div>

        {/* Uploaded Documents List */}
        {uploadedFiles.length > 0 && (
          <div className="bg-[#141414] border border-[#282828] rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between text-xs font-medium text-[#888888] pb-1.5 border-b border-[#222222]">
              <span>Uploaded Documents ({uploadedFiles.length})</span>
              <button
                type="button"
                onClick={handleExtractAndAutoFill}
                disabled={isExtracting}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow transition flex items-center gap-1.5 cursor-pointer"
              >
                {isExtracting ? (
                  <>
                    <span className="w-2.5 h-2.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    <span>Extracting...</span>
                  </>
                ) : (
                  <>
                    <span>✨</span>
                    <span>Upload & Auto-Fill</span>
                  </>
                )}
              </button>
            </div>

            <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
              {uploadedFiles.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between bg-[#1a1a1a] px-3 py-2 rounded-lg border border-[#2a2a2a] text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-purple-400 font-mono text-[10px]">MD</span>
                    <span className="text-white truncate font-medium">{f.filename}</span>
                    <span className="text-[#666666] font-mono text-[10px]">
                      ({(f.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {f.status === 'extracting' && (
                      <span className="text-purple-400 text-[10px] animate-pulse">Extracting...</span>
                    )}
                    {f.status === 'extracted' && (
                      <span className="text-emerald-400 text-[10px] flex items-center gap-1">
                        <span>✓</span>
                        <span>Extracted</span>
                      </span>
                    )}
                    {f.status === 'ready' && (
                      <span className="text-[#888888] text-[10px]">Ready</span>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveFile(f.id);
                      }}
                      className="text-[#666666] hover:text-red-400 text-xs px-1.5 py-0.5 rounded cursor-pointer"
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Part B: Optional Website Enrichment */}
      <div className="space-y-2 pt-2 border-t border-[#242424]">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-[#cccccc] flex items-center gap-2">
            <span>B. Optional Website Enrichment</span>
            <span className="text-[10px] text-[#666666] font-normal">(Scrapes public positioning & products)</span>
          </label>
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <span className="absolute left-3 top-2.5 text-[#666666] text-xs">🌐</span>
            <input
              type="text"
              value={websiteUrlInput}
              onChange={(e) => setWebsiteUrlInput(e.target.value)}
              placeholder="https://yourcompany.com"
              className="w-full pl-8 pr-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white placeholder-[#555555] outline-none font-mono"
            />
          </div>
          <button
            type="button"
            onClick={handleEnrichFromWebsite}
            disabled={isScraping || !websiteUrlInput.trim()}
            className="px-4 py-2 bg-[#222222] hover:bg-[#2c2c2c] disabled:opacity-50 text-[#d4d4d4] hover:text-white border border-[#333333] text-xs font-medium rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shrink-0"
          >
            {isScraping ? (
              <>
                <span className="w-2.5 h-2.5 rounded-full border-2 border-purple-400/30 border-t-purple-400 animate-spin" />
                <span>Scraping Website...</span>
              </>
            ) : (
              <>
                <span>Enrich from Website</span>
              </>
            )}
          </button>
        </div>

        {scrapeError && (
          <div className="text-xs text-red-400 bg-red-950/20 border border-red-900/40 p-2 rounded-lg">
            {scrapeError}
          </div>
        )}
        {scrapeSuccessMsg && (
          <div className="text-xs text-emerald-400 bg-emerald-950/20 border border-emerald-900/40 p-2 rounded-lg">
            {scrapeSuccessMsg}
          </div>
        )}
      </div>

      {/* Part C: Extraction Summary Banner */}
      {extractionSummary && (
        <div className="bg-purple-950/20 border border-purple-900/40 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-base">✨</span>
            <span className="text-purple-300 font-medium">
              Extracted {extractionSummary.extractedCount} fields from {extractionSummary.sources.join(', ')}.
            </span>
          </div>
          <div className="flex items-center gap-3">
            {extractionSummary.missingRequiredCount > 0 ? (
              <span className="text-amber-400 font-mono text-[11px]">
                {extractionSummary.missingRequiredCount} required fields need review
              </span>
            ) : (
              <span className="text-emerald-400 font-mono text-[11px]">
                All required fields populated
              </span>
            )}
          </div>
        </div>
      )}

      {/* Part D: Company Information Form */}
      <div className="space-y-5 pt-3 border-t border-[#242424]">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[#888888]">
            Company Information Specification
          </h3>
          <span className="text-[11px] text-[#666666] font-mono">
            {requiredFieldKeys.length - missingFieldsList.length}/{requiredFieldKeys.length} Required Filled
          </span>
        </div>

        {/* Row 1: Company Name & Stage */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FieldWrapper
            label="Company Name"
            required={true}
            fieldKey="company_name"
            provenance={provenance.company_name}
            isMissing={!formData.company_name.trim()}
          >
            <input
              type="text"
              value={formData.company_name}
              onChange={(e) => handleFieldChange('company_name', e.target.value)}
              placeholder="e.g. NimbusDesk, CloudPulse Inc."
              className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white placeholder-[#555555] outline-none"
            />
          </FieldWrapper>

          <FieldWrapper
            label="Company Stage"
            required={true}
            fieldKey="stage"
            provenance={provenance.stage}
            isMissing={!formData.stage.trim()}
          >
            <select
              value={formData.stage}
              onChange={(e) => handleFieldChange('stage', e.target.value)}
              className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white outline-none cursor-pointer"
            >
              <option value="">Select Stage...</option>
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </FieldWrapper>
        </div>

        {/* Row 2: Industry & Business Model */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FieldWrapper
            label="Industry"
            required={true}
            fieldKey="industry"
            provenance={provenance.industry}
            isMissing={!formData.industry.trim()}
          >
            <select
              value={formData.industry}
              onChange={(e) => handleFieldChange('industry', e.target.value)}
              className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white outline-none cursor-pointer"
            >
              <option value="">Select Industry...</option>
              {INDUSTRIES.map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
          </FieldWrapper>

          <FieldWrapper
            label="Business Model"
            required={true}
            fieldKey="business_model"
            provenance={provenance.business_model}
            isMissing={!formData.business_model.trim()}
          >
            <select
              value={formData.business_model}
              onChange={(e) => handleFieldChange('business_model', e.target.value)}
              className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white outline-none cursor-pointer"
            >
              <option value="">Select Business Model...</option>
              {BUSINESS_MODELS.map((bm) => (
                <option key={bm} value={bm}>
                  {bm}
                </option>
              ))}
            </select>
          </FieldWrapper>
        </div>

        {/* Long Text Field: Company Description */}
        <MarkdownFieldWrapper
          label="Company Description"
          required={true}
          fieldKey="description"
          value={formData.description}
          onChange={(val) => handleFieldChange('description', val)}
          placeholder="Comprehensive summary of company mission, customer problem solved, and core positioning..."
          provenance={provenance.description}
          isMissing={!formData.description.trim()}
          isPreview={activePreviews['description'] || false}
          onTogglePreview={() => togglePreview('description')}
        />

        {/* Long Text Field: Products & Services */}
        <MarkdownFieldWrapper
          label="Products & Services"
          required={true}
          fieldKey="products_services"
          value={formData.products_services}
          onChange={(val) => handleFieldChange('products_services', val)}
          placeholder="Detail main products, plan tiers, add-ons, technical architecture offerings..."
          provenance={provenance.products_services}
          isMissing={!formData.products_services.trim()}
          isPreview={activePreviews['products_services'] || false}
          onTogglePreview={() => togglePreview('products_services')}
        />

        {/* Long Text Field: Target Customers */}
        <MarkdownFieldWrapper
          label="Target Customers"
          required={true}
          fieldKey="target_customers"
          value={formData.target_customers}
          onChange={(val) => handleFieldChange('target_customers', val)}
          placeholder="Ideal customer profiles (ICP), company sizes, buyer personas, decision makers..."
          provenance={provenance.target_customers}
          isMissing={!formData.target_customers.trim()}
          isPreview={activePreviews['target_customers'] || false}
          onTogglePreview={() => togglePreview('target_customers')}
        />

        {/* Long Text Field: Revenue Model */}
        <MarkdownFieldWrapper
          label="Revenue Model"
          required={true}
          fieldKey="revenue_model"
          value={formData.revenue_model}
          onChange={(val) => handleFieldChange('revenue_model', val)}
          placeholder="How pricing is structured, billing cycles, contract terms, gross margins, usage rates..."
          provenance={provenance.revenue_model}
          isMissing={!formData.revenue_model.trim()}
          isPreview={activePreviews['revenue_model'] || false}
          onTogglePreview={() => togglePreview('revenue_model')}
        />

        {/* Long Text Field: Strategic Goals */}
        <MarkdownFieldWrapper
          label="Strategic Goals"
          required={true}
          fieldKey="strategic_goals"
          value={formData.strategic_goals}
          onChange={(val) => handleFieldChange('strategic_goals', val)}
          placeholder="Top priorities for the next 12-24 months (e.g. ARR milestone, profitability, international expansion)..."
          provenance={provenance.strategic_goals}
          isMissing={!formData.strategic_goals.trim()}
          isPreview={activePreviews['strategic_goals'] || false}
          onTogglePreview={() => togglePreview('strategic_goals')}
        />

        {/* Optional Long Text Field: Major Challenges */}
        <MarkdownFieldWrapper
          label="Major Challenges"
          required={false}
          fieldKey="major_challenges"
          value={formData.major_challenges}
          onChange={(val) => handleFieldChange('major_challenges', val)}
          placeholder="Operational bottlenecks, customer churn factors, competitive pressure, margin compression risks..."
          provenance={provenance.major_challenges}
          isMissing={false}
          isPreview={activePreviews['major_challenges'] || false}
          onTogglePreview={() => togglePreview('major_challenges')}
        />

        {/* Row 3: Optional Text Fields (Geographic Presence & Key Competitors) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FieldWrapper
            label="Geographic Presence"
            required={false}
            fieldKey="geographic_presence"
            provenance={provenance.geographic_presence}
            isMissing={false}
          >
            <input
              type="text"
              value={formData.geographic_presence}
              onChange={(e) => handleFieldChange('geographic_presence', e.target.value)}
              placeholder="e.g. North America, EMEA, APAC or HQ City"
              className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white placeholder-[#555555] outline-none"
            />
          </FieldWrapper>

          <FieldWrapper
            label="Key Competitors"
            required={false}
            fieldKey="key_competitors"
            provenance={provenance.key_competitors}
            isMissing={false}
          >
            <input
              type="text"
              value={formData.key_competitors}
              onChange={(e) => handleFieldChange('key_competitors', e.target.value)}
              placeholder="e.g. Zendesk, Intercom, Freshdesk"
              className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white placeholder-[#555555] outline-none"
            />
          </FieldWrapper>
        </div>
      </div>

      {/* Part E: Review & Save Action Bar */}
      <div className="pt-5 border-t border-[#242424] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          {saveError && (
            <div className="text-xs text-red-400 bg-red-950/20 border border-red-900/40 px-3 py-2 rounded-lg">
              {saveError}
            </div>
          )}
          {saveSuccessMsg && (
            <div className="text-xs text-emerald-400 bg-emerald-950/20 border border-emerald-900/40 px-3 py-2 rounded-lg flex items-center gap-1.5">
              <span>✓</span>
              <span>{saveSuccessMsg}</span>
            </div>
          )}
          {!saveError && !saveSuccessMsg && missingFieldsList.length > 0 && (
            <div className="text-[11px] text-amber-400/90 font-mono flex items-center gap-1.5">
              <span>⚠️</span>
              <span>
                {missingFieldsList.length} required field{missingFieldsList.length > 1 ? 's' : ''} left to fill
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-lg shadow-purple-600/20 transition flex items-center gap-2 cursor-pointer"
          >
            {isSaving ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                <span>Saving Company Context...</span>
              </>
            ) : (
              <>
                <span>💾</span>
                <span>Save Company Context</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

// Field wrapper helper
const FieldWrapper: React.FC<{
  label: string;
  required: boolean;
  fieldKey: string;
  provenance?: FieldProvenance;
  isMissing: boolean;
  children: React.ReactNode;
}> = ({ label, required, provenance, isMissing, children }) => {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <label className="text-[#cccccc] font-medium flex items-center gap-1">
          <span>{label}</span>
          {required ? (
            <span className="text-purple-400 font-bold">*</span>
          ) : (
            <span className="text-[10px] text-[#666666] font-normal">(Optional)</span>
          )}
        </label>

        {provenance?.extracted && (
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 flex items-center gap-1"
            title={`Source: ${provenance.source_detail || provenance.source}`}
          >
            <span>✨</span>
            <span>Extracted</span>
          </span>
        )}
        {provenance?.source === 'website_scraper' && (
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 flex items-center gap-1"
            title={`Scraped from ${provenance.source_detail}`}
          >
            <span>🌐</span>
            <span>Website</span>
          </span>
        )}
        {isMissing && required && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
            Missing
          </span>
        )}
      </div>
      {children}
    </div>
  );
};

// Markdown long text field wrapper
const MarkdownFieldWrapper: React.FC<{
  label: string;
  required: boolean;
  fieldKey: string;
  value: string;
  onChange: (val: string) => void;
  placeholder: string;
  provenance?: FieldProvenance;
  isMissing: boolean;
  isPreview: boolean;
  onTogglePreview: () => void;
}> = ({
  label,
  required,
  value,
  onChange,
  placeholder,
  provenance,
  isMissing,
  isPreview,
  onTogglePreview
}) => {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <label className="text-[#cccccc] font-medium flex items-center gap-1">
            <span>{label}</span>
            {required ? (
              <span className="text-purple-400 font-bold">*</span>
            ) : (
              <span className="text-[10px] text-[#666666] font-normal">(Optional)</span>
            )}
          </label>

          {provenance?.extracted && (
            <span
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 flex items-center gap-1"
              title={`Source: ${provenance.source_detail || provenance.source}`}
            >
              <span>✨</span>
              <span>Auto-Extracted</span>
            </span>
          )}
          {provenance?.source === 'website_scraper' && (
            <span
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 flex items-center gap-1"
              title={`Scraped from ${provenance.source_detail}`}
            >
              <span>🌐</span>
              <span>Website</span>
            </span>
          )}
          {isMissing && required && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
              Missing
            </span>
          )}
        </div>

        {/* Edit / Preview toggle */}
        <div className="flex items-center gap-1 bg-[#141414] border border-[#2e2e2e] p-0.5 rounded-lg">
          <button
            type="button"
            onClick={onTogglePreview}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition cursor-pointer ${
              !isPreview ? 'bg-[#2a2a2a] text-white font-bold' : 'text-[#888888] hover:text-white'
            }`}
          >
            Edit (MD)
          </button>
          <button
            type="button"
            onClick={onTogglePreview}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition cursor-pointer ${
              isPreview ? 'bg-[#2a2a2a] text-white font-bold' : 'text-[#888888] hover:text-white'
            }`}
          >
            Preview
          </button>
        </div>
      </div>

      {isPreview ? (
        <div className="w-full min-h-[96px] max-h-56 overflow-y-auto px-3.5 py-2.5 bg-[#141414] border border-[#2e2e2e] rounded-xl text-xs text-[#d4d4d4] prose prose-invert prose-xs max-w-none">
          {value ? (
            <div className="whitespace-pre-wrap leading-relaxed font-sans">{value}</div>
          ) : (
            <span className="text-[#555555] italic">No content to preview</span>
          )}
        </div>
      ) : (
        <textarea
          rows={3}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full px-3 py-2 bg-[#141414] border border-[#2e2e2e] focus:border-purple-500 rounded-xl text-xs text-white placeholder-[#555555] outline-none font-mono leading-relaxed resize-y min-h-[76px]"
        />
      )}
    </div>
  );
};
