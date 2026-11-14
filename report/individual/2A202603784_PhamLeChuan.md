# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline

- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: Commodity Markets Outlook, October 2026. Corpus là `starter/data/book.pdf`, gồm 70 trang PDF, trong đó 68 trang có nội dung trích xuất được. Số trang trong metadata và benchmark là số trang vật lý của PDF, bắt đầu từ 1. Quyền sử dụng và chia sẻ tài liệu cần được xác nhận theo nguồn cung cấp.
- Chuẩn hóa, lỗi và giới hạn: PDF được đọc bằng `pypdf`. Text được chuẩn hóa Unicode NFKC, khoảng trắng và dòng xuống. Một số trang có bố cục bảng/biểu đồ và text extraction không hoàn hảo. Một số fixed-size chunks bị cắt giữa câu hoặc mất một phần ký tự ở ranh giới chunk.
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí: Sử dụng `sentence-transformers/all-MiniLM-L6-v2`, embedding local, 384 dimensions. Vector store là PostgreSQL với pgvector, Docker image `pgvector/pgvector:0.8.7-pg16`. Metric là cosine distance/similarity. Lệnh chạy chính: `python -m src.run`. Chi phí API: 0 vì sử dụng model local. Phiên bản `sentence-transformers` cần được ghi lại từ môi trường cài đặt thực tế.
- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn: Mỗi chunk giữ `document_id`, `source`, `page`. Metadata bổ sung gồm `section`, `category`, `document_type`, `has_text`, `content_chars` và `chunk_strategy`. Giá trị `section` và `category` được gán theo heading/phạm vi nội dung thực tế trong PDF. Các trường này được chọn để truy vết nguồn và giới hạn truy xuất theo phần báo cáo hoặc nhóm hàng hóa.

## Cấu hình và benchmark

- A / B / C:
  - A: fixed-size chunks, kích thước 500 ký tự, overlap 50 ký tự.
  - B: paragraph-based chunks, giới hạn tối đa 1.200 ký tự, không overlap.
  - C: giống B về chunking và embedding, nhưng áp dụng filter `section` hoặc `category` khi câu hỏi cung cấp filter.
- Có 20 câu hỏi, gồm 15 câu dev và 5 câu test. Có 6 câu sử dụng metadata filter, trong đó 2 câu thuộc test. Mỗi câu có expected answer, gold source, gold page và evidence quote. Evidence được kiểm tra trực tiếp trong nội dung PDF.
- Tiêu chí chọn chiến lược đã chốt trước khi xem test: ưu tiên Evidence Hit@3, sau đó Hit@1, chất lượng grounding/coherence, tính hữu dụng của metadata và chi phí/tài nguyên.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---|---|
| A_fixed | dev | 0/15 | 4/15 | 647 | Not recorded | $0 |
| A_fixed | test | 0/5 | 1/5 | 647 | Not recorded | $0 |
| B_paragraph | dev | 3/15 | 4/15 | 268 | Not recorded | $0 |
| B_paragraph | test | 1/5 | 1/5 | 268 | Not recorded | $0 |
| C_paragraph_filter | dev | 3/15 | 4/15 | 268 | Not recorded | $0 |
| C_paragraph_filter | test | 1/5 | 1/5 | 268 | Not recorded | $0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---:|---:|---:|---|
| A_fixed | 1.4/2 (5 câu test) | 15/15 | N/A | 0:1, 1:0, 2:4; trung bình 1.6/2 |
| B_paragraph | 1.6/2 (5 câu test) | 15/15 | N/A | 0:1, 1:1, 2:3; trung bình 1.4/2 |
| C_paragraph_filter | 1.6/2 (5 câu test) | 15/15 | 2/2 | 0:1, 1:1, 2:3; trung bình 1.4/2 |

Đường dẫn trace, nhãn thủ công và cách chọn mẫu:

- Trace đầy đủ: `starter/results/traces.json`
- Retrieval metrics: `starter/results/metrics.json`
- Nhãn thủ công: `starter/results/manual_evaluation.csv`
- Mẫu đánh giá thủ công: 5 câu test giống nhau cho cả ba strategy.
- Coherence được đánh giá trên các chunk top-3 của 5 câu test. Để đáp ứng đầy đủ rubric, cần bổ sung đánh giá trên 10 vị trí nội dung cố định.

## Phân tích và kết luận

- B so với A: B cải thiện Hit@1 trên dev từ 0/15 lên 3/15 và trên test từ 0/5 lên 1/5. Paragraph-based chunking giữ ngữ cảnh tốt hơn và tạo ít chunk hơn. Tuy nhiên, một số evidence vẫn bị chia hoặc không nằm trong top-3.
- B so với C: C có cùng số chunk và embedding với B, đồng thời filter được áp dụng đúng trên 2 câu test có filter. Tuy nhiên, C không cải thiện điểm so với B trên bộ test nhỏ.
- Ví dụ lỗi:
  - q17: A không trả về đủ evidence dù top-1 ở đúng trang; chunk bị chia và text extraction có khác biệt định dạng.
  - q18: cả B và C không đưa được đoạn chứa danh sách copper, maize, oil và silver vào top-3.
- Chiến lược được chọn: B — paragraph-based chunking. Chiến lược này cân bằng tốt hơn giữa tính mạch lạc, số lượng chunk và kết quả Hit@1. C phù hợp khi truy vấn có metadata đáng tin, nhưng lợi ích chưa thể hiện rõ trên test hiện tại.
- Đánh đổi: A đơn giản nhưng dễ cắt câu và tạo nhiều chunk. B ít chunk hơn và giữ ngữ cảnh tốt hơn. C tăng khả năng giới hạn phạm vi truy xuất nhưng phụ thuộc vào metadata chính xác.
- Hạn chế: Test chỉ có 5 câu; kết quả không thể khái quát cho corpus khác. Một số bảng/biểu đồ được trích xuất text chưa hoàn hảo. Thời gian chạy chưa được đo riêng cho từng strategy. Chi phí embedding local bằng 0 nhưng yêu cầu tải model và tài nguyên máy.
- Nếu làm lại hoặc mở rộng: cải thiện xử lý bảng/PDF layout, chia chunk theo câu hoặc heading, đo thời gian ingest/search, mở rộng bộ test và đánh giá coherence trên đủ 10 vị trí cố định.
