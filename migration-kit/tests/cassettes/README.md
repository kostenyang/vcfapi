# Cassettes — lab 錄下來的真實回應

每個 JSON 是一組 `rules`，回放器依序比對 `match`（method / path regex / 標頭條件 / 是否 Basic auth），
第一個命中的 `response` 就回去；都沒命中回 404。

* `source` 欄標明是哪一天、對哪個版本錄的；`note` 是當時觀察。
* body 只保留判斷用的最小欄位，token 值一律以 `<redacted>` 取代。
* **404 / 401 / 403 都是真實回應**，不是我們編的：舊端點在 9.1 就是這樣回。

重錄：`python tools/record_cassettes.py`（需要 lab 組態；不會把憑證寫進檔案）。
