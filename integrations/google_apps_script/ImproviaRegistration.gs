/** Improvia Google Form -> Aiven registration bridge.
 *
 * Bind this script to the Google Form response spreadsheet.
 * Form:
 * https://docs.google.com/forms/d/e/1FAIpQLSd6VhE8oq6D0CsNKY-mpVkpPuO45yg9VfF2HYmUorxzMsAp6w/viewform
 *
 * Script Properties:
 *   IMPROVIA_WEBHOOK_URL
 *   IMPROVIA_WEBHOOK_SECRET
 *
 * Add a sheet column named exactly: Enrollment Status
 */
const WEBHOOK_URL_PROPERTY = 'IMPROVIA_WEBHOOK_URL';
const WEBHOOK_SECRET_PROPERTY = 'IMPROVIA_WEBHOOK_SECRET';
const STATUS_HEADER = 'Enrollment Status';

function setupTriggers() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  ScriptApp.getUserTriggers(spreadsheet).forEach(function(trigger) {
    const handler = trigger.getHandlerFunction();
    if (handler === 'improviaOnFormSubmit' || handler === 'improviaOnEdit') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger('improviaOnFormSubmit')
    .forSpreadsheet(spreadsheet)
    .onFormSubmit()
    .create();

  ScriptApp.newTrigger('improviaOnEdit')
    .forSpreadsheet(spreadsheet)
    .onEdit()
    .create();
}

function improviaOnFormSubmit(e) {
  if (!e || !e.range) return;
  sendRowToImprovia_(e.range.getSheet(), e.range.getRow());
}

function improviaOnEdit(e) {
  if (!e || !e.range) return;
  const sheet = e.range.getSheet();
  const row = e.range.getRow();
  const col = e.range.getColumn();
  if (row === 1) return;

  const headers = getHeaders_(sheet);
  const statusCol = headers.indexOf(STATUS_HEADER) + 1;
  if (!statusCol || col !== statusCol) return;

  sendRowToImprovia_(sheet, row);
}

function sendRowToImprovia_(sheet, rowNumber) {
  const props = PropertiesService.getScriptProperties();
  const webhookUrl = (props.getProperty(WEBHOOK_URL_PROPERTY) || '').trim();
  const webhookSecret = (props.getProperty(WEBHOOK_SECRET_PROPERTY) || '').trim();

  if (!webhookUrl || !webhookSecret) {
    throw new Error('Set IMPROVIA_WEBHOOK_URL and IMPROVIA_WEBHOOK_SECRET in Script Properties.');
  }

  const headers = getHeaders_(sheet);
  const values = sheet.getRange(rowNumber, 1, 1, headers.length).getDisplayValues()[0];
  const row = {};

  headers.forEach(function(header, index) {
    if (header) row[header] = values[index];
  });

  const response = UrlFetchApp.fetch(webhookUrl, {
    method: 'post',
    contentType: 'application/json',
    headers: {'X-Improvia-Webhook-Secret': webhookSecret},
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
    throw new Error('Improvia webhook failed: HTTP ' + code + ' ' + body);
  }
}

function getHeaders_(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn())
    .getDisplayValues()[0]
    .map(function(value) { return String(value).trim(); });
}
