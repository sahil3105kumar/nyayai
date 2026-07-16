/*
  upload / poll / fetch result - matches the real backend flow:
  POST /upload -> {job_id}, GET /status/{job_id} -> {status}, GET /result/{job_id} -> report.

  everything here is mocked with setTimeout to simulate real async latency.
  once api/routes exists, only the bodies of these three functions change -
  every call site elsewhere in the app stays the same.
*/

import { buildMockReport } from './mockData'

const MOCK_JOBS = new Map()

export async function uploadPdf(file) {
  const jobId = `mock-job-${Date.now()}`
  MOCK_JOBS.set(jobId, { status: 'PENDING', file })

  // simulate the pipeline taking a moment (OCR -> model -> rules -> renderer)
  setTimeout(() => {
    const job = MOCK_JOBS.get(jobId)
    if (job) job.status = 'STARTED'
  }, 400)

  setTimeout(() => {
    const job = MOCK_JOBS.get(jobId)
    if (job) {
      job.status = 'SUCCESS'
      job.report = buildMockReport(file.name)
    }
  }, 1600)

  return { jobId }
}

export async function pollJobStatus(jobId) {
  const job = MOCK_JOBS.get(jobId)
  if (!job) throw new Error(`unknown job: ${jobId}`)
  return { status: job.status }
}

export async function fetchResult(jobId) {
  const job = MOCK_JOBS.get(jobId)
  if (!job || job.status !== 'SUCCESS') {
    throw new Error(`job ${jobId} is not finished yet`)
  }
  return job.report
}
