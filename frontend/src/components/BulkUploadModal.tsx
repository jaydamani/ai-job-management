import React, { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { bulkUploadResumes } from '../api/candidates'
import type { BulkUploadItemResult, BulkUploadResponse } from '../types'

interface Props {
  jobId: string
  onClose: () => void
}

function scoreColorClass(score?: number | null): string {
  if (score == null) return 'bg-gray-100 text-gray-500'
  if (score >= 70) return 'bg-green-600 text-white'
  if (score >= 40) return 'bg-yellow-400 text-yellow-900'
  return 'bg-red-500 text-white'
}

function FileRow({ file, onRemove }: { file: File; onRemove: () => void }) {
  return (
    <li className="flex items-center justify-between bg-gray-50 rounded-md px-3 py-2 text-sm">
      <span className="flex items-center gap-2 text-gray-700 min-w-0">
        <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <span className="truncate">{file.name}</span>
        <span className="text-gray-400 shrink-0">({(file.size / 1024).toFixed(0)} KB)</span>
      </span>
      <button
        type="button"
        onClick={onRemove}
        aria-label="Remove file"
        className="ml-2 shrink-0 text-gray-300 hover:text-red-500 focus:outline-none"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </li>
  )
}

function ResultRow({ item, rank, jobId, onClose }: { item: BulkUploadItemResult; rank: number; jobId: string; onClose: () => void }) {
  return (
    <div className="flex items-center gap-3 bg-gray-50 rounded-lg p-3">
      <span className="text-xs font-semibold text-gray-400 w-5 shrink-0 tabular-nums">#{rank}</span>
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums shrink-0 ${scoreColorClass(item.fit_score)}`}>
        {item.fit_score != null ? `${item.fit_score}%` : '–'}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
        {item.email && <p className="text-xs text-gray-400 truncate">{item.email}</p>}
        {item.fit_explanation && (
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{item.fit_explanation}</p>
        )}
      </div>
      {item.candidate_id && (
        <Link
          to={`/jobs/${jobId}/candidates/${item.candidate_id}`}
          onClick={onClose}
          className="text-xs text-blue-600 hover:text-blue-700 shrink-0 font-medium"
        >
          View →
        </Link>
      )}
    </div>
  )
}

export default function BulkUploadModal({ jobId, onClose }: Props) {
  const [files, setFiles] = useState<File[]>([])
  const [dragging, setDragging] = useState(false)
  const [result, setResult] = useState<BulkUploadResponse | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (selectedFiles: File[]) => bulkUploadResumes(jobId, selectedFiles),
    onSuccess: (data) => {
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ['candidates', jobId] })
    },
  })

  const addFiles = (incoming: FileList | File[]) => {
    const pdfs = Array.from(incoming).filter(
      (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
    )
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name))
      const fresh = pdfs.filter((f) => !existing.has(f.name))
      return [...prev, ...fresh].slice(0, 20)
    })
  }

  const removeFile = (idx: number) => setFiles((prev) => prev.filter((_, i) => i !== idx))

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }

  const handleSubmit = () => {
    if (files.length === 0 || mutation.isPending) return
    mutation.mutate(files)
  }

  const reset = () => {
    setFiles([])
    setResult(null)
    mutation.reset()
  }

  const succeeded = result?.results.filter((r) => r.status === 'success') ?? []
  const failed = result?.results.filter((r) => r.status === 'failed') ?? []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Bulk Resume Upload</h2>
            <p className="text-xs text-gray-400 mt-0.5">Upload multiple PDFs — candidates are created and ranked by AI fit score</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

          {/* Upload phase */}
          {!result && !mutation.isPending && (
            <>
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  dragging
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  multiple
                  onChange={(e) => e.target.files && addFiles(e.target.files)}
                  className="sr-only"
                />
                <svg className="mx-auto w-10 h-10 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm font-medium text-gray-700">Drop PDF resumes here or click to browse</p>
                <p className="text-xs text-gray-400 mt-1">Up to 20 files · 5 MB each</p>
              </div>

              {files.length > 0 && (
                <ul className="space-y-2">
                  {files.map((f, i) => (
                    <FileRow key={f.name} file={f} onRemove={() => removeFile(i)} />
                  ))}
                </ul>
              )}

              {mutation.isError && (
                <p className="text-sm text-red-600">Upload failed. Please try again.</p>
              )}
            </>
          )}

          {/* Processing */}
          {mutation.isPending && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <svg className="animate-spin w-10 h-10 text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3V4a10 10 0 00-10 10h4z" />
              </svg>
              <div className="text-center">
                <p className="text-gray-700 font-medium">
                  Processing {files.length} resume{files.length !== 1 ? 's' : ''}…
                </p>
                <p className="text-sm text-gray-400 mt-1">AI is parsing and scoring each one. This may take a minute.</p>
              </div>
            </div>
          )}

          {/* Results */}
          {result && (
            <>
              <div className="flex items-center gap-3">
                <span className="text-sm text-green-700 bg-green-50 px-2.5 py-1 rounded-full font-medium">
                  {result.succeeded} processed
                </span>
                {result.failed > 0 && (
                  <span className="text-sm text-red-700 bg-red-50 px-2.5 py-1 rounded-full font-medium">
                    {result.failed} failed
                  </span>
                )}
              </div>

              {succeeded.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-700">Ranked by Fit Score</h3>
                  {succeeded.map((item, i) => (
                    <ResultRow
                      key={item.candidate_id ?? i}
                      item={item}
                      rank={i + 1}
                      jobId={jobId}
                      onClose={onClose}
                    />
                  ))}
                </div>
              )}

              {failed.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-700">Failed</h3>
                  {failed.map((item, i) => (
                    <div key={i} className="flex items-start gap-2 bg-red-50 rounded-lg p-3">
                      <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div>
                        <p className="text-sm font-medium text-red-700">{item.name}</p>
                        {item.error && <p className="text-xs text-red-500 mt-0.5">{item.error}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between gap-3">
          {result ? (
            <>
              <button
                type="button"
                onClick={reset}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium focus:outline-none"
              >
                Upload more
              </button>
              <button
                type="button"
                onClick={onClose}
                className="text-sm bg-gray-900 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-700"
              >
                Done
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="text-sm text-gray-500 hover:text-gray-700 focus:outline-none"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={files.length === 0 || mutation.isPending}
                className="text-sm bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors font-medium disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                Upload &amp; Rank{files.length > 0 ? ` (${files.length})` : ''}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
