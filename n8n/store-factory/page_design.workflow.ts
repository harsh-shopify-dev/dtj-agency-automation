import { workflow, node, trigger, sticky, ifElse, expr } from '@n8n/workflow-sdk';

const briefReady = trigger({
  type: 'n8n-nodes-base.executeWorkflowTrigger',
  version: 1.2,
  config: {
    name: 'When a Brief Is Ready',
    position: [0, 0],
    parameters: { inputSource: 'workflowInputs', workflowInputs: { values: [{ name: 'row_id', type: 'number' }] } },
  },
  output: [{ row_id: 1 }],
});

const loadBrief = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Load Brief',
    position: [240, 0],
    parameters: {
      resource: 'row',
      operation: 'get',
      dataTableId: { __rl: true, mode: 'list', value: '7FWesTH7eVyLNuOQ', cachedResultName: 'dtj_client_intake' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'id', condition: 'eq', keyValue: expr('{{ $json.row_id }}') }] },
      returnAll: false,
      limit: 1,
    },
  },
  output: [{ id: 1, status: 'new', brand_name: 'TOILOVA', store_domain: 'elevate-with-harsh.myshopify.com', theme_id: '188893495469', brand_json: '{}', facts_json: '{}', picture_links_json: '[]' }],
});

const requestDesign = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Request for Claude Code: Page Design',
    position: [480, 0],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `// Claude Code designs this page instead of the Claude API (Harsh's choice, 9 Oct 2026: the same hand-off as the dtj content workflow).
// Claude Code reads "request" from this node's output, runs the page builder on Harsh's PC
// (services/store-builder: python -m page_builder.run_client --intake <this output as JSON> --plan answer --copy answer ...),
// shows Harsh the plan and the screenshots, then POSTs to resume_url:
// {"page_status": "ready for approval" | "needs a look" | "could not build", "approve_code": "<12 hex, only when ready>",
//  "summary": "<the plan in two or three sentences>", "sections": ["..."], "note": "<anything Harsh should know>"}
const row = $input.first().json;
if (!row || !row.id) throw new Error('No brief with that row id in dtj_client_intake');
return [{ json: {
  claude_code_stage: 'page_design',
  resume_url: $execution.resumeUrl,
  request: {
    row_id: row.id, brand_name: row.brand_name, store_domain: row.store_domain, theme_id: row.theme_id || '',
    status: row.status, problems: row.problems || '',
    brand: JSON.parse(row.brand_json || '{}'), facts: JSON.parse(row.facts_json || '{}'),
    picture_links: JSON.parse(row.picture_links_json || '[]'), logo_link: row.logo_link || '', notes: row.notes || '',
  },
} }];`,
    },
  },
  output: [{ claude_code_stage: 'page_design', resume_url: 'https://example/webhook-waiting/1', request: { row_id: 1 } }],
});

const waitDesign = node({
  type: 'n8n-nodes-base.wait',
  version: 1.1,
  config: {
    name: 'Wait for Claude Code: Page Design',
    position: [720, 0],
    parameters: { resume: 'webhook', httpMethod: 'POST', limitWaitTime: true, limitType: 'afterTimeInterval', resumeAmount: 3, resumeUnit: 'days', options: {} },
  },
  output: [{ body: { page_status: 'ready for approval', approve_code: '0123456789ab', summary: 'Plan', sections: ['faq'] } }],
});

const replyDesign = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Claude Code Reply: Page Design',
    position: [960, 0],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `// Reads what Claude Code posted to the Wait node (a timeout resumes with no body) and keeps only well-formed values.
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['ready for approval', 'needs a look', 'could not build'];
let status = allowed.includes(b.page_status) ? b.page_status : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 3 days)');
const code = /^[0-9a-f]{12}$/.test(String(b.approve_code || '')) ? String(b.approve_code) : '';
if (status === 'ready for approval' && !code) status = 'reply not understood (no approval code)';
return [{ json: {
  row_id: $('Load Brief').first().json.id,
  page_status: status,
  approve_code: status === 'ready for approval' ? code : '',
  page_summary: String(b.summary || ''),
  page_sections: Array.isArray(b.sections) ? b.sections.map(String).join(', ') : '',
  page_note: String(b.note || ''),
} }];`,
    },
  },
  output: [{ row_id: 1, page_status: 'ready for approval', approve_code: '0123456789ab', page_summary: 'Plan', page_sections: 'faq', page_note: '' }],
});

const recordDesign = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Record Page Design',
    position: [1200, 0],
    parameters: {
      resource: 'row',
      operation: 'update',
      dataTableId: { __rl: true, mode: 'list', value: '7FWesTH7eVyLNuOQ', cachedResultName: 'dtj_client_intake' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'id', condition: 'eq', keyValue: expr('{{ $json.row_id }}') }] },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          page_status: expr('{{ $json.page_status }}'),
          approve_code: expr('{{ $json.approve_code }}'),
          page_summary: expr('{{ $json.page_summary }}'),
          page_sections: expr('{{ $json.page_sections }}'),
          page_note: expr('{{ $json.page_note }}'),
          page_updated_at: expr('{{ $now.toISO() }}'),
        },
        schema: [
          { id: 'page_status', displayName: 'page_status', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'approve_code', displayName: 'approve_code', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'page_summary', displayName: 'page_summary', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'page_sections', displayName: 'page_sections', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'page_note', displayName: 'page_note', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'page_updated_at', displayName: 'page_updated_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
        ],
      },
      options: {},
    },
  },
  output: [{ id: 1 }],
});

const readyForApproval = ifElse({
  version: 2.3,
  config: {
    name: 'Ready for Approval?',
    position: [1200, 240],
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 },
        conditions: [{ leftValue: expr("{{ $('Claude Code Reply: Page Design').item.json.page_status }}"), rightValue: 'ready for approval', operator: { type: 'string', operation: 'equals' } }],
        combinator: 'and',
      },
    },
  },
});

const requestWrite = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Request for Claude Code: Write to Draft',
    position: [1440, 240],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `// Second hand-off. Claude Code writes the page into the client's DRAFT theme only after Harsh says yes to this exact page
// (python -m page_builder.push_page --out <run folder> --approve <approve_code> --approved-by <name>; it refuses the live theme),
// then POSTs to resume_url: {"result": "written to draft" | "not written", "approved_by": "<name>", "note": "<what happened>"}
const d = $('Claude Code Reply: Page Design').first().json;
const brief = $('Load Brief').first().json;
return [{ json: {
  claude_code_stage: 'write_to_draft',
  resume_url: $execution.resumeUrl,
  request: { row_id: d.row_id, approve_code: d.approve_code, store_domain: brief.store_domain, theme_id: brief.theme_id || '' },
} }];`,
    },
  },
  output: [{ claude_code_stage: 'write_to_draft', resume_url: 'https://example/webhook-waiting/1', request: { row_id: 1 } }],
});

const waitWrite = node({
  type: 'n8n-nodes-base.wait',
  version: 1.1,
  config: {
    name: 'Wait for Claude Code: Write to Draft',
    position: [1680, 240],
    parameters: { resume: 'webhook', httpMethod: 'POST', limitWaitTime: true, limitType: 'afterTimeInterval', resumeAmount: 14, resumeUnit: 'days', options: {} },
  },
  output: [{ body: { result: 'written to draft', approved_by: 'Harsh', note: '' } }],
});

const replyWrite = node({
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {
    name: 'Claude Code Reply: Write to Draft',
    position: [1920, 240],
    parameters: {
      mode: 'runOnceForAllItems',
      language: 'javaScript',
      jsCode: `// Reads what Claude Code posted after the write (a timeout resumes with no body).
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['written to draft', 'not written'];
const result = allowed.includes(b.result) ? b.result : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 14 days)');
return [{ json: {
  row_id: $('Claude Code Reply: Page Design').first().json.row_id,
  page_status: result,
  approved_by: result === 'written to draft' ? String(b.approved_by || '') : '',
  page_note: String(b.note || ''),
} }];`,
    },
  },
  output: [{ row_id: 1, page_status: 'written to draft', approved_by: 'Harsh', page_note: '' }],
});

const recordWrite = node({
  type: 'n8n-nodes-base.dataTable',
  version: 1.1,
  config: {
    name: 'Record Write to Draft',
    position: [2160, 240],
    parameters: {
      resource: 'row',
      operation: 'update',
      dataTableId: { __rl: true, mode: 'list', value: '7FWesTH7eVyLNuOQ', cachedResultName: 'dtj_client_intake' },
      matchType: 'allConditions',
      filters: { conditions: [{ keyName: 'id', condition: 'eq', keyValue: expr('{{ $json.row_id }}') }] },
      columns: {
        mappingMode: 'defineBelow',
        value: {
          page_status: expr('{{ $json.page_status }}'),
          approved_by: expr('{{ $json.approved_by }}'),
          page_note: expr('{{ $json.page_note }}'),
          page_updated_at: expr('{{ $now.toISO() }}'),
        },
        schema: [
          { id: 'page_status', displayName: 'page_status', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'approved_by', displayName: 'approved_by', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'page_note', displayName: 'page_note', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
          { id: 'page_updated_at', displayName: 'page_updated_at', required: false, defaultMatch: false, display: true, type: 'string', canBeUsedToMatch: true },
        ],
      },
      options: {},
    },
  },
  output: [{ id: 1 }],
});

const about = sticky(
  '## Store factory: page design (Claude Code hand-off)\n' +
  'Started by "Shopify Automation" when a brief is saved with status `new` (or by hand with a `row_id`).\n\n' +
  '1. **Page Design**: the run pauses. Claude Code (Harsh\'s desktop session) reads the request, designs the page with the page builder ' +
  '(plan and copy written by Claude Code, checked by code), shows Harsh, and posts the result with an approval code. Nothing touches the store.\n' +
  '2. **Write to Draft**: the run pauses again. Only after Harsh says yes to that exact page does Claude Code write it into the client\'s ' +
  'DRAFT theme (never the live theme) and post the result.\n\n' +
  'Every step is recorded on the brief\'s row in **dtj_client_intake** (page_status, approve_code, approved_by). Source in git: `n8n/store-factory/`.',
  [briefReady, loadBrief, requestDesign, waitDesign, replyDesign, recordDesign],
  { color: 5, position: [-40, -420], width: 1300, height: 300 },
);

export default workflow('store-factory-page-design', 'Store Factory: Page Design')
  .add(briefReady)
  .to(loadBrief)
  .to(requestDesign)
  .to(waitDesign)
  .to(replyDesign)
  .to(recordDesign)
  .add(replyDesign)
  .to(readyForApproval.onTrue(requestWrite.to(waitWrite.to(replyWrite.to(recordWrite)))))
  .add(about);
