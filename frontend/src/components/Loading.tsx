export function Loading({ message = 'Ładowanie danych rynkowych...' }: { message?: string }) {
  return (
    <div className="loading">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error">
      <p>{message}</p>
      <button className="btn btn-primary" onClick={onRetry}>Ponów</button>
    </div>
  )
}
