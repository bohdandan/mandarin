import { writtenChineseUrl } from "./lib/written-chinese";
import { getDisplayTags, type VocabularyEntry } from "./lib/vocabulary";

type VocabularyDetailDialogProps = {
  entry: VocabularyEntry;
  onClose: () => void;
};

export function VocabularyDetailDialog({ entry, onClose }: VocabularyDetailDialogProps) {
  return (
    <article
      aria-labelledby="detail-title"
      aria-modal="true"
      className="detail-dialog"
      role="dialog"
      onClick={(event) => event.stopPropagation()}
    >
      <div className="detail-header">
        <div>
          <h2 id="detail-title">{entry.hanzi}</h2>
          <div className="detail-pinyin-row">
            <p>{entry.pinyin}</p>
          </div>
        </div>
        <button className="close-button" type="button" onClick={onClose}>
          Close
        </button>
      </div>
      <p className="meaning">{entry.english}</p>
      {entry.example_sentence ? <p className="example" dangerouslySetInnerHTML={{ __html: entry.example_sentence }} /> : null}
      {entry.sentence_pinyin ? <p className="sentence-pinyin">{entry.sentence_pinyin}</p> : null}
      {entry.sentence_translation ? <p className="sentence-translation">{entry.sentence_translation}</p> : null}
      {entry.notes ? <p className="notes">{entry.notes}</p> : null}
      <div className="detail-meta-row">
        <div className="tag-row">
          {getDisplayTags(entry).map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
        <a
          aria-label="Character breakdown"
          className="detail-meta-link"
          href={writtenChineseUrl(entry.hanzi)}
          rel="noreferrer"
          target="_blank"
          title="Character breakdown"
        >
          ◫
        </a>
      </div>
    </article>
  );
}
