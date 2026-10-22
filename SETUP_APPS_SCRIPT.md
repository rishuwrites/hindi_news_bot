# Google Apps Script scheduler

The Apps Script scheduler starts the GitHub Actions workflows in India Standard
Time (IST):

- **Short news:** 7:00, 8:30, 10:00, 12:00, 13:30, 15:00, 16:30, and 18:30;
- **Long news:** 06:00 and 18:00. Long videos are scheduled to publish at
  08:00 and 20:00.

Apps Script clock triggers run approximately near the requested minute, not
exactly on the minute. The short workflow schedules each upload for the next
available time in `src/config.py`; this scheduler controls when video creation
starts, not the short video's publication time.

## Install

1. Open [script.google.com](https://script.google.com) and create a project.
2. Copy the contents of [`Code.gs`](./Code.gs) into the Apps Script editor.
3. In **Project Settings > Script properties**, add `GITHUB_PAT` with a GitHub
   personal access token that can dispatch Actions workflows in this repository
   (for a fine-grained token, grant repository access and **Actions: read/write**).
   Do not put the token in the source file.
4. Set the Apps Script project time zone to **Asia/Kolkata** in Project Settings.
5. Select `setupTriggers` in the editor and run it once; approve the requested
   permissions. It installs 10 daily triggers and replaces only earlier triggers
   created by this scheduler.

The script consumes 10 trigger slots, so make sure the account's Apps Script
trigger quota has room. If GitHub rejects a dispatch, the Apps Script execution
fails with the HTTP status and response body in its execution log.

These triggers replace the workflows' built-in cron schedules; manual
`workflow_dispatch` runs remain available from the GitHub Actions page.
