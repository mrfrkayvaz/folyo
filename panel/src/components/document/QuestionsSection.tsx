interface QuestionsSectionProps {
  questions?: string[]
}

export default function QuestionsSection({ questions = [] }: QuestionsSectionProps) {
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-base-content/50">
        Çıkarılan Sorular ({questions.length})
      </h3>
      <div className="mt-2 flex flex-col gap-1.5">
        {questions.length > 0 ? (
          questions.map((q, i) => (
            <div key={`${q}-${i}`} className="rounded-xl border border-base-300 bg-base-100 px-3 py-2">
              <span className="font-mono text-xs text-base-content/40">{i + 1}.</span>{" "}
              <span className="text-sm text-base-content/80">{q}</span>
            </div>
          ))
        ) : (
          <p className="text-xs text-base-content/40">Bu belgeden soru çıkarılmadı.</p>
        )}
      </div>
    </section>
  )
}