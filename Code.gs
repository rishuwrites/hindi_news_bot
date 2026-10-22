const GITHUB_OWNER = "rishuwrites";
const GITHUB_REPO = "hindi_news_bot";
const GITHUB_BRANCH = "main";
const SHORT_WORKFLOW = "make-video.yml";
const LONG_WORKFLOW = "bulletin.yml";
const TIME_ZONE = "Asia/Kolkata";

const SHORT_RUN_TIMES = [
  [7, 0], [8, 30], [10, 0], [12, 0],
  [13, 30], [15, 0], [16, 30], [18, 30]
];
const LONG_RUN_TIMES = [[6, 0], [18, 0]];
const MANAGED_HANDLERS = ["triggerShortNews", "triggerLongNews"];

function setupTriggers() {
  if (!PropertiesService.getScriptProperties().getProperty("GITHUB_PAT")) {
    throw new Error("Set the GITHUB_PAT script property before installing triggers.");
  }

  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (MANAGED_HANDLERS.indexOf(trigger.getHandlerFunction()) !== -1) {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  SHORT_RUN_TIMES.forEach(function (time) {
    createDailyTrigger("triggerShortNews", time[0], time[1]);
  });
  LONG_RUN_TIMES.forEach(function (time) {
    createDailyTrigger("triggerLongNews", time[0], time[1]);
  });

  Logger.log("Installed 8 short-news and 2 long-news daily triggers in " + TIME_ZONE + ".");
}

function createDailyTrigger(handler, hour, minute) {
  ScriptApp.newTrigger(handler)
    .timeBased()
    .atHour(hour)
    .nearMinute(minute)
    .everyDays(1)
    .inTimezone(TIME_ZONE)
    .create();
}

function triggerShortNews() {
  dispatchWorkflow(SHORT_WORKFLOW, {
    publish_now: "false",
    upload: "true"
  });
}

function triggerLongNews() {
  dispatchWorkflow(LONG_WORKFLOW, {
    publish_now: "false",
    upload: "true",
    test_mode: "false"
  });
}

function dispatchWorkflow(workflowFile, inputs) {
  const token = PropertiesService.getScriptProperties().getProperty("GITHUB_PAT");
  if (!token) {
    throw new Error("Missing GITHUB_PAT script property.");
  }

  const url = "https://api.github.com/repos/" + GITHUB_OWNER + "/" + GITHUB_REPO +
    "/actions/workflows/" + workflowFile + "/dispatches";
  const response = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    payload: JSON.stringify({ ref: GITHUB_BRANCH, inputs: inputs }),
    muteHttpExceptions: true
  });

  if (response.getResponseCode() !== 204) {
    throw new Error("GitHub dispatch failed for " + workflowFile + " (HTTP " +
      response.getResponseCode() + "): " + response.getContentText());
  }
  Logger.log("Dispatched " + workflowFile + " successfully.");
}
