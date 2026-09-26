/** Improvia Google Form -> Aiven registration bridge.
 *
 * This script is bound to the Google Form. The Form must already be linked
 * to its response spreadsheet and the response sheet must contain:
 *   Enrollment Status
 *
 * Script Properties:
 *   IMPROVIA_WEBHOOK_URL
 *   IMPROVIA_WEBHOOK_SECRET
 *
 * Only an explicit approved enrollment status triggers the webhook.
 */
const WEBHOOK_URL_PROPERTY = 'IMPROVIA_WEBHOOK_URL';
const WEBHOOK_SECRET_PROPERTY = 'IMPROVIA_WEBHOOK_SECRET';
const STATUS_HEADER = 'Enrollment Status';
const APPROVED_STATUSES = ['APPROVED', 'ENROLLED', 'ACTIVE'];

function setupImprovia() {
  const form = FormApp.getActiveForm();
  if (!form) {
    throw new Error('Open this Apps Script from the Google Form.');
  }

  const destinationId = form.getDestinationId();
  if (!destinationId) {
    throw new Error('Link this Google Form to a response spreadsheet first.');
  }

  const spreadsheet = SpreadsheetApp.openById(destinationId);

  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    const handler = trigger.getHandlerFunction();
    if (handler === 'improviaEnrollmentStatusEdit' ||
        handler === 'improviaOnFormSubmit' ||
        handler === 'improviaOnEdit') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger('improviaEnrollmentStatusEdit')
    .forSpreadsheet(spreadsheet)
    .onEdit()
    .create();
}

function improviaEnrollmentStatusEdit(e) {
  if (!e || !e.range) return;

  const sheet = e.range.getSheet();
  const headers = getHeaders_(sheet);
  const statusCol = headers.findIndex(function(header) {
    return header.toLowerCase() === STATUS_HEADER.toLowerCase();
  }) + 1;

  if (!statusCol) return;

  const firstCol = e.range.getColumn();
  const lastCol = firstCol + e.range.getNumColumns() - 1;
  if (statusCol < firstCol || statusCol > lastCol) return;

  const firstRow = Math.max(2, e.range.getRow());
  const lastRow = e.range.getRow() + e.range.getNumRows() - 1;

  for (let row = firstRow; row <= lastRow; row++) {
    const status = String(
      sheet.getRange(row, statusCol).getDisplayValue() || ''
    ).trim().toUpperCase();

    if (!APPROVED_STATUSES.includes(status)) continue;

    sendRowToImprovia_(sheet, row);
  }
}

function sendRowToImprovia_(sheet, rowNumber) {
  const props = PropertiesService.getScriptProperties();
  const webhookUrl = (props.getProperty(WEBHOOK_URL_PROPERTY) || '').trim();
  const webhookSecret = (props.getProperty(WEBHOOK_SECRET_PROPERTY) || '').trim();

  if (!webhookUrl || !webhookSecret) {
    throw new Error(
      'Set IMPROVIA_WEBHOOK_URL and IMPROVIA_WEBHOOK_SECRET in Script Properties.'
    );
  }

  const headers = getHeaders_(sheet);
  const values = sheet.getRange(
    rowNumber, 1, 1, headers.length
  ).getDisplayValues()[0];

  const row = {};
  headers.forEach(function(header, index) {
    if (header) row[header] = values[index];
  });

  const response = UrlFetchApp.fetch(webhookUrl, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'X-Improvia-Webhook-Secret': webhookSecret
    },
    payload: JSON.stringify({
      source: 'google_form_response_sheet',
      row_number: rowNumber,
      row: row
    }),
    muteHttpExceptions: true
  });

  const code = response.getResponseCode();
  const body = response.getContentText();
  console.log('Improvia webhook response: ' + code + ' ' + body);

  if (code < 200 || code >= 300) {
    throw new Error(
      'Improvia webhook failed: HTTP ' + code + ' ' + body
    );
  }
}

function getHeaders_(sheet) {
  return sheet.getRange(
    1, 1, 1, sheet.getLastColumn()
  ).getDisplayValues()[0].map(function(value) {
    return String(value).trim();
  });
}
