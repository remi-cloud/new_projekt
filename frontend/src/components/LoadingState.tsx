export default function LoadingState({ message = 'Ładowanie…' }: { message?: string }) {
  return (
    <div className="loading">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="error">
      <p>{message}</p>
      {onRetry && (
        <button className="btn btn-primary" onClick={onRetry} type="button">
          Ponów
        </button>
      )}
    </div>
  )
}
