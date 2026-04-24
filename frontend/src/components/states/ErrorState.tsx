// Shown when the analyze call fails. Surfaces a meaningful message and a
// retry control. Errors from the typed client carry status + body; we
// don't dump those raw at the user, but a developer can read them in the
// network tab.

interface Props {
  message: string;
  onRetry: () => void;
}

export default function ErrorState({ message, onRetry }: Props) {
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-900">
      <p className="font-medium">Analysis failed.</p>
      <p className="mt-1 text-sm">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-900 hover:bg-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
      >
        Try again
      </button>
    </div>
  );
}
