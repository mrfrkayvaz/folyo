import MessageList from "./MessageList.jsx"
import ReadyState from "./ReadyState.jsx"
import UploadingState from "./UploadingState.jsx"
import Welcome from "./Welcome.jsx"

export default function ChatMain({
  routeLoading,
  uploading,
  statusText,
  messages,
  onCitationClick,
  allReady,
  totalCount,
  attachments,
  onAsk,
  workspace,
  onPickFile,
  onDropFiles,
}) {
  return (
    <main className="ctx-scroll min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 sm:px-6">
        {routeLoading ? (
          <div className="flex flex-1 items-center justify-center py-24">
            <span className="loading loading-spinner loading-lg text-base-content/20" />
          </div>
        ) : uploading && messages.length === 0 ? (
          <UploadingState statusText={statusText} />
        ) : messages.length > 0 ? (
          <MessageList messages={messages} onCitationClick={onCitationClick} />
        ) : allReady ? (
          <ReadyState
            totalCount={totalCount}
            attachments={attachments}
            onAsk={onAsk}
            workspace={workspace}
          />
        ) : (
          <Welcome onPickFile={onPickFile} onDropFiles={onDropFiles} />
        )}
      </div>
    </main>
  )
}