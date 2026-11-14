# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline

- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: Commodity Markets Outlook, October 2026. Corpus là `starter/data/book.pdf`, gồm 70 trang PDF, trong đó 68 trang có nội dung trích xuất được. Số trang dùng trong metadata và benchmark là số trang vật lý PDF, bắt đầu từ 1. Quyền sử dụng và chia sẻ tài liệu cần được xác nhận theo nguồn cung cấp.
- Chuẩn hóa, lỗi và giới hạn: PDF được đọc bằng `pypdf`. Text được chuẩn hóa Unicode NFKC, khoảng trắng và dòng xuống. Một số bảng và biểu đồ có thể bị trích xuất chưa hoàn hảo. Fixed-size chunks có thể bị cắt giữa câu hoặc mất một phần ký tự ở ranh giới chunk.
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí: Sử dụng `sentence-transformers/all-MiniLM-L6-v2`, embedding local, 384 dimensions. Vector store là PostgreSQL với Docker image `pgvector/pgvector:0.8.7-pg16`. Metric là cosine similarity/distance. Lệnh chạy: `python -m src.run`. Chi phí API: $0 vì dùng model local.
- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn: Mỗi chunk giữ `document_id`, `source`, `page`. Metadata bổ sung gồm `section`, `category`, `document_type`, `has_text`, `content_chars` và `chunk_strategy`. `section` và `category` được gán theo phạm vi nội dung thực tế trong PDF để truy vết và lọc kết quả.

## Cấu hình và benchmark

- A: fixed-size chunks, kích thước 500 ký tự, overlap 50 ký tự.
- B: paragraph-based chunks, giới hạn tối đa 800 ký tự, không overlap.
- C: giống B về chunking và embedding, nhưng áp dụng filter `section` hoặc `category` khi câu hỏi có filter.
- Có 20 câu hỏi, gồm 15 dev và 5 test. Có 6 câu sử dụng metadata filter, trong đó 2 câu thuộc test. Mỗi câu có expected answer, gold source, gold page và evidence quote.
- Tiêu chí chọn strategy: ưu tiên Evidence Hit@3 trên dev, sau đó Hit@1, coherence, metadata usefulness và chi phí/tài nguyên. Không dùng test để điều chỉnh tham số.

## Kết quả

| Strategy | Chunk count | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 |
|---|---:|---:|---:|---:|---:|
| A_fixed | 647 | 1/15 | 5/15 | 2/5 | 3/5 |
| B_paragraph | 388 | 3/15 | 4/15 | 1/5 | 2/5 |
| C_paragraph_filter | 388 | 3/15 | 4/15 | 1/5 | 2/5 |

### Đánh giá thủ công

| Strategy | Coherence trung bình /2 | Metadata đủ và đúng | Filter tuân thủ | Grounding trung bình /2 |
|---|---:|---:|---:|---:|
| A_fixed | 1.4/2 | 15/15 | N/A | 1.6/2 |
| B_paragraph | 1.6/2 | 15/15 | N/A | 1.4/2 |
| C_paragraph_filter | 1.6/2 | 15/15 | 2/2 | 1.4/2 |

Đường dẫn kết quả:

- Trace: `starter/results/traces.json`
- Metrics: `starter/results/metrics.json`
- Nhãn thủ công: `starter/results/manual_evaluation.csv`
- Experiment log: `artifacts/experiment_log.csv`

## Phân tích và kết luận

- A đạt Evidence Hit@3 cao nhất trên dev: 5/15, so với 4/15 của B và C.
- B đạt Hit@1 cao nhất trên dev: 3/15. Paragraph chunking tạo 388 chunks, ít hơn A và giữ ngữ cảnh tốt hơn.
- C có cùng chunk và embedding với B. Filter hoạt động nhưng chưa tạo cải thiện so với B trên bộ test nhỏ.
- A có lợi thế về Evidence Hit@3 trong lần chạy này, nhưng fixed-size dễ cắt câu và tạo nhiều chunk hơn.
- B có lợi thế về coherence và chi phí lưu trữ thấp hơn. Nếu ưu tiên Hit@1 và tính mạch lạc, B là lựa chọn phù hợp. Nếu ưu tiên Evidence Hit@3 theo tiêu chí đã chốt, A có kết quả tốt hơn trên lần chạy này.
- Một lỗi tiêu biểu là q18: top-3 không chứa đầy đủ danh sách copper, maize, oil và silver. Một số câu khác bị ảnh hưởng bởi cách trích xuất text và khác biệt dấu câu trong PDF.
- Hạn chế: test chỉ có 5 câu, một số bảng/biểu đồ không được trích xuất hoàn hảo, thời gian chạy chưa được đo riêng và kết quả chưa thể khái quát cho corpus khác.
- Nếu làm lại, cần đánh giá thủ công lại theo `traces.json` mới, cải thiện xử lý bảng/PDF layout, thử chunk theo câu/heading và đo thời gian ingest/search.