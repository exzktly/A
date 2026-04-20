# runtime_app.py Attribute Call Audit

Total callsites in runtime_app.py: **1621**\
Flagged non-migrated in runtime_app.py: **0**\

| line | receiver | method | migrated_pyside | reason |
|---:|---|---|---|---|
| 307 | `logging` | `getLogger` | true | Qt-safe/default |
| 342 | `combo` | `clear` | true | Qt-safe/default |
| 343 | `combo` | `addItems` | true | Qt-safe/default |
| 359 | `_np` | `asarray` | true | Qt-safe/default |
| 360 | `arr` | `min` | true | Qt-safe/default |
| 361 | `arr` | `max` | true | Qt-safe/default |
| 364 | `(_np.clip(arr, alo, ahi) - alo) / (ahi - alo) * 255` | `astype` | true | Qt-safe/default |
| 364 | `_np` | `clip` | true | Qt-safe/default |
| 365 | `_np.stack([disp, disp, disp], axis=-1)` | `copy` | true | Qt-safe/default |
| 365 | `_np` | `stack` | true | Qt-safe/default |
| 367 | `QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)` | `copy` | true | Qt-safe/default |
| 368 | `QPixmap` | `fromImage` | true | Qt-safe/default |
| 369 | `pm` | `scaled` | true | Qt-safe/default |
| 376 | `_np` | `asarray` | true | Qt-safe/default |
| 378 | `arr` | `astype` | true | Qt-safe/default |
| 379 | `arr_f` | `min` | true | Qt-safe/default |
| 379 | `arr_f` | `max` | true | Qt-safe/default |
| 382 | `(arr_f - lo) / (hi - lo) * 255` | `astype` | true | Qt-safe/default |
| 383 | `_np.stack([disp, disp, disp], axis=-1)` | `copy` | true | Qt-safe/default |
| 383 | `_np` | `stack` | true | Qt-safe/default |
| 387 | `a` | `max` | true | Qt-safe/default |
| 387 | `a` | `min` | true | Qt-safe/default |
| 388 | `(a.astype(_np.float32) - a.min()) / rng * 255` | `astype` | true | Qt-safe/default |
| 388 | `a` | `astype` | true | Qt-safe/default |
| 388 | `a` | `min` | true | Qt-safe/default |
| 389 | `_np` | `ascontiguousarray` | true | Qt-safe/default |
| 393 | `QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)` | `copy` | true | Qt-safe/default |
| 394 | `QPixmap` | `fromImage` | true | Qt-safe/default |
| 395 | `pm` | `scaled` | true | Qt-safe/default |
| 410 | `layout` | `count` | true | Qt-safe/default |
| 411 | `layout` | `takeAt` | true | Qt-safe/default |
| 412 | `item` | `widget` | true | Qt-safe/default |
| 414 | `w` | `setParent` | true | Qt-safe/default |
| 415 | `w` | `deleteLater` | true | Qt-safe/default |
| 417 | `item` | `layout` | true | Qt-safe/default |
| 425 | `lb` | `setSelectionMode` | true | Qt-safe/default |
| 429 | `lb` | `addItem` | true | Qt-safe/default |
| 431 | `item` | `setSelected` | true | Qt-safe/default |
| 437 | `lb.item(i)` | `text` | true | Qt-safe/default |
| 437 | `lb` | `item` | true | Qt-safe/default |
| 437 | `lb` | `count` | true | Qt-safe/default |
| 437 | `lb.item(i)` | `isSelected` | true | Qt-safe/default |
| 437 | `lb` | `item` | true | Qt-safe/default |
| 445 | `QFileDialog` | `getSaveFileName` | true | Qt-safe/default |
| 452 | `json` | `dump` | true | Qt-safe/default |
| 455 | `QMessageBox` | `critical` | true | Qt-safe/default |
| 463 | `QFileDialog` | `getOpenFileName` | true | Qt-safe/default |
| 470 | `json` | `load` | true | Qt-safe/default |
| 472 | `QMessageBox` | `critical` | true | Qt-safe/default |
| 483 | `ax` | `set_facecolor` | true | Qt-safe/default |
| 484 | `ax.spines` | `values` | true | Qt-safe/default |
| 485 | `sp` | `set_color` | true | Qt-safe/default |
| 486 | `sp` | `set_linewidth` | true | Qt-safe/default |
| 487 | `ax` | `tick_params` | true | Qt-safe/default |
| 488 | `ax.xaxis.label` | `set_color` | true | Qt-safe/default |
| 489 | `ax.yaxis.label` | `set_color` | true | Qt-safe/default |
| 490 | `ax` | `set_title` | true | Qt-safe/default |
| 491 | `ax` | `set_ylabel` | true | Qt-safe/default |
| 492 | `ax` | `grid` | true | Qt-safe/default |
| 510 | `tp` | `strip` | true | Qt-safe/default |
| 515 | `re` | `fullmatch` | true | Qt-safe/default |
| 516 | `m` | `groups` | true | Qt-safe/default |
| 517 | `m` | `group` | true | Qt-safe/default |
| 517 | `m` | `group` | true | Qt-safe/default |
| 517 | `m` | `group` | true | Qt-safe/default |
| 520 | `re` | `fullmatch` | true | Qt-safe/default |
| 523 | `m` | `group` | true | Qt-safe/default |
| 523 | `m.group(2)[0]` | `lower` | true | Qt-safe/default |
| 523 | `m` | `group` | true | Qt-safe/default |
| 536 | `re` | `search` | true | Qt-safe/default |
| 538 | `m` | `group` | true | Qt-safe/default |
| 551 | `row` | `get` | true | Qt-safe/default |
| 560 | `path` | `open` | true | Qt-safe/default |
| 561 | `csv` | `DictReader` | true | Qt-safe/default |
| 565 | `row` | `items` | true | Qt-safe/default |
| 566 | `str(k).strip()` | `lower` | true | Qt-safe/default |
| 566 | `str(k)` | `strip` | true | Qt-safe/default |
| 568 | `str(v)` | `strip` | true | Qt-safe/default |
| 577 | `rows` | `append` | true | Qt-safe/default |
| 592 | `rows[0]` | `keys` | true | Qt-safe/default |
| 593 | `col` | `endswith` | true | Qt-safe/default |
| 596 | `channels` | `append` | true | Qt-safe/default |
| 611 | `rows[0]` | `keys` | true | Qt-safe/default |
| 612 | `col` | `endswith` | true | Qt-safe/default |
| 615 | `channels` | `append` | true | Qt-safe/default |
| 626 | `str(rows[0].get('channel', '') or '').strip()` | `lower` | true | Qt-safe/default |
| 626 | `str(rows[0].get('channel', '') or '')` | `strip` | true | Qt-safe/default |
| 626 | `rows[0]` | `get` | true | Qt-safe/default |
| 634 | `str(tok or '').strip()` | `lower` | true | Qt-safe/default |
| 634 | `str(tok or '')` | `strip` | true | Qt-safe/default |
| 637 | `seen` | `add` | true | Qt-safe/default |
| 638 | `out` | `append` | true | Qt-safe/default |
| 649 | `str(seg_channel_token or '').strip()` | `lower` | true | Qt-safe/default |
| 649 | `str(seg_channel_token or '')` | `strip` | true | Qt-safe/default |
| 651 | `merged` | `append` | true | Qt-safe/default |
| 667 | `str(ch or '').strip()` | `lower` | true | Qt-safe/default |
| 667 | `str(ch or '')` | `strip` | true | Qt-safe/default |
| 669 | `seen` | `add` | true | Qt-safe/default |
| 670 | `chans` | `append` | true | Qt-safe/default |
| 671 | `str(seg_channel_token or '').strip()` | `lower` | true | Qt-safe/default |
| 671 | `str(seg_channel_token or '')` | `strip` | true | Qt-safe/default |
| 673 | `seen` | `add` | true | Qt-safe/default |
| 674 | `chans` | `append` | true | Qt-safe/default |
| 698 | `row` | `get` | true | Qt-safe/default |
| 699 | `math` | `isnan` | true | Qt-safe/default |
| 701 | `row` | `get` | true | Qt-safe/default |
| 703 | `raw_strings` | `add` | true | Qt-safe/default |
| 764 | `row` | `get` | true | Qt-safe/default |
| 773 | `fluor_gates` | `items` | true | Qt-safe/default |
| 776 | `row` | `get` | true | Qt-safe/default |
| 788 | `row` | `get` | true | Qt-safe/default |
| 789 | `math` | `isnan` | true | Qt-safe/default |
| 792 | `row` | `get` | true | Qt-safe/default |
| 795 | `ordinals` | `get` | true | Qt-safe/default |
| 809 | `all_v[t]` | `append` | true | Qt-safe/default |
| 811 | `above_v[t]` | `append` | true | Qt-safe/default |
| 815 | `above_v` | `get` | true | Qt-safe/default |
| 821 | `statistics` | `pstdev` | true | Qt-safe/default |
| 822 | `math` | `sqrt` | true | Qt-safe/default |
| 823 | `result` | `append` | true | Qt-safe/default |
| 832 | `math` | `isfinite` | true | Qt-safe/default |
| 860 | `row` | `get` | true | Qt-safe/default |
| 868 | `fluor_gates` | `items` | true | Qt-safe/default |
| 871 | `row` | `get` | true | Qt-safe/default |
| 885 | `math` | `isfinite` | true | Qt-safe/default |
| 889 | `result` | `append` | true | Qt-safe/default |
| 923 | `bins.setdefault(b, [])` | `append` | true | Qt-safe/default |
| 923 | `bins` | `setdefault` | true | Qt-safe/default |
| 925 | `bins` | `values` | true | Qt-safe/default |
| 929 | `bins` | `values` | true | Qt-safe/default |
| 949 | `re` | `escape` | true | Qt-safe/default |
| 951 | `sfx` | `replace` | true | Qt-safe/default |
| 952 | `re` | `compile` | true | Qt-safe/default |
| 952 | `'\|'` | `join` | true | Qt-safe/default |
| 958 | `re` | `compile` | true | Qt-safe/default |
| 959 | `re` | `compile` | true | Qt-safe/default |
| 960 | `re` | `compile` | true | Qt-safe/default |
| 973 | `re` | `search` | true | Qt-safe/default |
| 974 | `m.group(1)` | `upper` | true | Qt-safe/default |
| 974 | `m` | `group` | true | Qt-safe/default |
| 974 | `m` | `group` | true | Qt-safe/default |
| 993 | `self.zip_member` | `split` | true | Qt-safe/default |
| 1038 | `_FNAME_RE` | `match` | true | Qt-safe/default |
| 1040 | `m` | `group` | true | Qt-safe/default |
| 1040 | `m` | `group` | true | Qt-safe/default |
| 1041 | `_logger` | `debug` | true | Qt-safe/default |
| 1049 | `pipeline_info` | `get` | true | Qt-safe/default |
| 1051 | `str(f)` | `strip` | true | Qt-safe/default |
| 1051 | `pipeline_info` | `get` | true | Qt-safe/default |
| 1052 | `str(f)` | `strip` | true | Qt-safe/default |
| 1055 | `str(pipeline_info.get('schema', ''))` | `strip` | true | Qt-safe/default |
| 1055 | `pipeline_info` | `get` | true | Qt-safe/default |
| 1056 | `f` | `strip` | true | Qt-safe/default |
| 1056 | `schema` | `split` | true | Qt-safe/default |
| 1056 | `f` | `strip` | true | Qt-safe/default |
| 1059 | `stem` | `split` | true | Qt-safe/default |
| 1086 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 1087 | `_logger` | `debug` | true | Qt-safe/default |
| 1124 | `data_dir` | `glob` | true | Qt-safe/default |
| 1125 | `p.name` | `startswith` | true | Qt-safe/default |
| 1127 | `_OUT_ZIP_RE` | `match` | true | Qt-safe/default |
| 1128 | `m` | `group` | true | Qt-safe/default |
| 1128 | `m` | `group` | true | Qt-safe/default |
| 1129 | `out_zips` | `append` | true | Qt-safe/default |
| 1131 | `_PLAIN_ZIP_RE` | `match` | true | Qt-safe/default |
| 1132 | `m2` | `group` | true | Qt-safe/default |
| 1132 | `m2` | `group` | true | Qt-safe/default |
| 1133 | `plain_zips` | `append` | true | Qt-safe/default |
| 1140 | `in_dir` | `glob` | true | Qt-safe/default |
| 1141 | `p.name` | `startswith` | true | Qt-safe/default |
| 1143 | `_PLAIN_ZIP_RE` | `match` | true | Qt-safe/default |
| 1144 | `m` | `group` | true | Qt-safe/default |
| 1144 | `m` | `group` | true | Qt-safe/default |
| 1145 | `result` | `append` | true | Qt-safe/default |
| 1152 | `out_dir` | `glob` | true | Qt-safe/default |
| 1153 | `p.name` | `startswith` | true | Qt-safe/default |
| 1155 | `_OUT_ZIP_RE` | `match` | true | Qt-safe/default |
| 1156 | `m` | `group` | true | Qt-safe/default |
| 1156 | `m` | `group` | true | Qt-safe/default |
| 1157 | `result` | `append` | true | Qt-safe/default |
| 1179 | `_logger` | `info` | true | Qt-safe/default |
| 1180 | `folder_path` | `iterdir` | true | Qt-safe/default |
| 1181 | `p` | `is_file` | true | Qt-safe/default |
| 1183 | `p.suffix` | `lower` | true | Qt-safe/default |
| 1183 | `p.name` | `startswith` | true | Qt-safe/default |
| 1196 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1198 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1200 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1202 | `mask` | `setdefault` | true | Qt-safe/default |
| 1204 | `smfish` | `setdefault` | true | Qt-safe/default |
| 1206 | `_logger` | `warning` | true | Qt-safe/default |
| 1246 | `fluor_token` | `lower` | true | Qt-safe/default |
| 1252 | `_logger` | `info` | true | Qt-safe/default |
| 1259 | `_debug_flags` | `review_image_load_debug_enabled` | true | Qt-safe/default |
| 1260 | `_debug_flags` | `movie_montage_load_debug_enabled` | true | Qt-safe/default |
| 1262 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 1264 | `_logger` | `debug` | true | Qt-safe/default |
| 1274 | `in_dir` | `is_dir` | true | Qt-safe/default |
| 1280 | `g` | `items` | true | Qt-safe/default |
| 1281 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1283 | `ov` | `items` | true | Qt-safe/default |
| 1284 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1285 | `mk` | `items` | true | Qt-safe/default |
| 1286 | `mask` | `setdefault` | true | Qt-safe/default |
| 1287 | `th` | `items` | true | Qt-safe/default |
| 1288 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1290 | `data_dir` | `is_dir` | true | Qt-safe/default |
| 1297 | `g` | `items` | true | Qt-safe/default |
| 1298 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1299 | `ov` | `items` | true | Qt-safe/default |
| 1300 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1301 | `mk` | `items` | true | Qt-safe/default |
| 1302 | `mask` | `setdefault` | true | Qt-safe/default |
| 1303 | `th` | `items` | true | Qt-safe/default |
| 1304 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1309 | `in_dir` | `is_dir` | true | Qt-safe/default |
| 1313 | `_logger` | `info` | true | Qt-safe/default |
| 1317 | `g` | `items` | true | Qt-safe/default |
| 1318 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1319 | `ov` | `items` | true | Qt-safe/default |
| 1320 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1321 | `mk` | `items` | true | Qt-safe/default |
| 1322 | `mask` | `setdefault` | true | Qt-safe/default |
| 1323 | `th` | `items` | true | Qt-safe/default |
| 1324 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1326 | `_logger` | `info` | true | Qt-safe/default |
| 1328 | `data_dir` | `is_dir` | true | Qt-safe/default |
| 1332 | `_logger` | `info` | true | Qt-safe/default |
| 1336 | `g` | `items` | true | Qt-safe/default |
| 1337 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1338 | `ov` | `items` | true | Qt-safe/default |
| 1339 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1340 | `mk` | `items` | true | Qt-safe/default |
| 1341 | `mask` | `setdefault` | true | Qt-safe/default |
| 1342 | `th` | `items` | true | Qt-safe/default |
| 1343 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1345 | `_logger` | `info` | true | Qt-safe/default |
| 1348 | `data_dir` | `is_dir` | true | Qt-safe/default |
| 1353 | `g` | `items` | true | Qt-safe/default |
| 1354 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1355 | `ov` | `items` | true | Qt-safe/default |
| 1356 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1357 | `mk` | `items` | true | Qt-safe/default |
| 1358 | `mask` | `setdefault` | true | Qt-safe/default |
| 1359 | `th` | `items` | true | Qt-safe/default |
| 1360 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1363 | `data_dir` | `is_dir` | true | Qt-safe/default |
| 1369 | `g` | `items` | true | Qt-safe/default |
| 1370 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1371 | `ov` | `items` | true | Qt-safe/default |
| 1372 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1373 | `mk` | `items` | true | Qt-safe/default |
| 1374 | `mask` | `setdefault` | true | Qt-safe/default |
| 1375 | `th` | `items` | true | Qt-safe/default |
| 1376 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1379 | `d` | `is_dir` | true | Qt-safe/default |
| 1380 | `data_dir` | `is_dir` | true | Qt-safe/default |
| 1384 | `search_root` | `rglob` | true | Qt-safe/default |
| 1385 | `p.suffix` | `lower` | true | Qt-safe/default |
| 1385 | `p.name` | `startswith` | true | Qt-safe/default |
| 1401 | `parsed` | `get` | true | Qt-safe/default |
| 1405 | `_logger` | `info` | true | Qt-safe/default |
| 1413 | `_FNAME_RE` | `match` | true | Qt-safe/default |
| 1414 | `m` | `group` | true | Qt-safe/default |
| 1417 | `_logger` | `info` | true | Qt-safe/default |
| 1426 | `_logger` | `info` | true | Qt-safe/default |
| 1434 | `_logger` | `info` | true | Qt-safe/default |
| 1442 | `fluor` | `setdefault` | true | Qt-safe/default |
| 1444 | `tophat_fluor` | `setdefault` | true | Qt-safe/default |
| 1446 | `overlay` | `setdefault` | true | Qt-safe/default |
| 1448 | `mask` | `setdefault` | true | Qt-safe/default |
| 1451 | `_logger` | `warning` | true | Qt-safe/default |
| 1453 | `_logger` | `info` | true | Qt-safe/default |
| 1455 | `_logger` | `warning` | true | Qt-safe/default |
| 1457 | `_logger` | `info` | true | Qt-safe/default |
| 1459 | `_logger` | `debug` | true | Qt-safe/default |
| 1467 | `fluor` | `items` | true | Qt-safe/default |
| 1467 | `overlay` | `items` | true | Qt-safe/default |
| 1468 | `mask` | `items` | true | Qt-safe/default |
| 1468 | `tophat_fluor` | `items` | true | Qt-safe/default |
| 1555 | `name` | `endswith` | true | Qt-safe/default |
| 1562 | `super()` | `__init__` | true | Qt-safe/default |
| 1660 | `self` | `_build_ui` | true | Qt-safe/default |
| 1661 | `self` | `_apply_theme` | true | Qt-safe/default |
| 1664 | `QTimer` | `singleShot` | true | Qt-safe/default |
| 1664 | `self` | `_load_path` | true | Qt-safe/default |
| 1674 | `root` | `geometry` | true | Qt-safe/default |
| 1682 | `self._cell_gating_tab._cell_area_threshold` | `get` | true | Qt-safe/default |
| 1690 | `self._cell_gating_tab` | `get_fluor_gate` | true | Qt-safe/default |
| 1701 | `self` | `_get_fluor_gate` | true | Qt-safe/default |
| 1710 | `self` | `_get_cell_area_threshold` | true | Qt-safe/default |
| 1711 | `self` | `_get_all_fluor_gates` | true | Qt-safe/default |
| 1714 | `self` | `_get_rows` | true | Qt-safe/default |
| 1718 | `row` | `get` | true | Qt-safe/default |
| 1725 | `fluor_gates` | `items` | true | Qt-safe/default |
| 1728 | `row` | `get` | true | Qt-safe/default |
| 1738 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 1741 | `self` | `_refresh_review_csv_rows` | true | Qt-safe/default |
| 1748 | `self._cell_gating_tab` | `get_thresh_frac_on` | true | Qt-safe/default |
| 1756 | `outer` | `setContentsMargins` | true | Qt-safe/default |
| 1757 | `outer` | `setSpacing` | true | Qt-safe/default |
| 1762 | `top_layout` | `setContentsMargins` | true | Qt-safe/default |
| 1765 | `self._dir_label` | `setObjectName` | true | Qt-safe/default |
| 1766 | `top_layout` | `addWidget` | true | Qt-safe/default |
| 1767 | `top_layout` | `addStretch` | true | Qt-safe/default |
| 1769 | `open_btn` | `setProperty` | true | Qt-safe/default |
| 1770 | `open_btn.clicked` | `connect` | true | Qt-safe/default |
| 1771 | `top_layout` | `addWidget` | true | Qt-safe/default |
| 1772 | `outer` | `addWidget` | true | Qt-safe/default |
| 1775 | `self._top_sep` | `setFrameShape` | true | Qt-safe/default |
| 1776 | `outer` | `addWidget` | true | Qt-safe/default |
| 1780 | `outer` | `addWidget` | true | Qt-safe/default |
| 1783 | `sidebar` | `setFixedWidth` | true | Qt-safe/default |
| 1785 | `sidebar_layout` | `setContentsMargins` | true | Qt-safe/default |
| 1788 | `QVBoxLayout(self._sidebar_main_frame)` | `setContentsMargins` | true | Qt-safe/default |
| 1789 | `sidebar_layout` | `addWidget` | true | Qt-safe/default |
| 1801 | `w` | `setParent` | true | Qt-safe/default |
| 1802 | `w` | `hide` | true | Qt-safe/default |
| 1804 | `self._h_pane` | `addWidget` | true | Qt-safe/default |
| 1805 | `self` | `_build_sidebar` | true | Qt-safe/default |
| 1809 | `QVBoxLayout(centre)` | `setContentsMargins` | true | Qt-safe/default |
| 1810 | `self._h_pane` | `addWidget` | true | Qt-safe/default |
| 1811 | `self._h_pane` | `setStretchFactor` | true | Qt-safe/default |
| 1812 | `self._h_pane` | `setStretchFactor` | true | Qt-safe/default |
| 1813 | `self` | `_build_centre` | true | Qt-safe/default |
| 1816 | `self` | `_build_bottom` | true | Qt-safe/default |
| 1866 | `self._stats_drag_visited` | `add` | true | Qt-safe/default |
| 1867 | `self` | `_stats_active_group` | true | Qt-safe/default |
| 1874 | `grp.members` | `append` | true | Qt-safe/default |
| 1877 | `grp.members` | `remove` | true | Qt-safe/default |
| 1881 | `grp.solo_wells` | `append` | true | Qt-safe/default |
| 1884 | `grp.solo_wells` | `remove` | true | Qt-safe/default |
| 1885 | `self` | `_stats_refresh_single_btn` | true | Qt-safe/default |
| 1893 | `self._stats_map_btns` | `get` | true | Qt-safe/default |
| 1900 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 1905 | `self` | `_mute_color` | true | Qt-safe/default |
| 1910 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 1926 | `self._well_paths` | `keys` | true | Qt-safe/default |
| 1931 | `tok_color` | `setdefault` | true | Qt-safe/default |
| 1933 | `self` | `_stats_active_group` | true | Qt-safe/default |
| 1936 | `active_wells` | `add` | true | Qt-safe/default |
| 1937 | `self._stats_map_btns` | `items` | true | Qt-safe/default |
| 1939 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 1952 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 1959 | `self` | `_mute_color` | true | Qt-safe/default |
| 1964 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 1978 | `container` | `layout` | true | Qt-safe/default |
| 1981 | `layout` | `setContentsMargins` | true | Qt-safe/default |
| 1982 | `layout` | `setSpacing` | true | Qt-safe/default |
| 1986 | `lbl` | `setObjectName` | true | Qt-safe/default |
| 1987 | `layout` | `addWidget` | true | Qt-safe/default |
| 1988 | `self` | `_stats_refresh_map` | true | Qt-safe/default |
| 1994 | `card` | `setObjectName` | true | Qt-safe/default |
| 1996 | `card` | `setProperty` | true | Qt-safe/default |
| 1998 | `hl` | `setContentsMargins` | true | Qt-safe/default |
| 2000 | `dot` | `setStyleSheet` | true | Qt-safe/default |
| 2001 | `hl` | `addWidget` | true | Qt-safe/default |
| 2002 | `hl` | `addWidget` | true | Qt-safe/default |
| 2006 | `parts` | `append` | true | Qt-safe/default |
| 2007 | `parts` | `append` | true | Qt-safe/default |
| 2009 | `', '` | `join` | true | Qt-safe/default |
| 2010 | `meta` | `setObjectName` | true | Qt-safe/default |
| 2011 | `hl` | `addWidget` | true | Qt-safe/default |
| 2012 | `hl` | `addStretch` | true | Qt-safe/default |
| 2015 | `ren_btn` | `setFlat` | true | Qt-safe/default |
| 2016 | `ren_btn.clicked` | `connect` | true | Qt-safe/default |
| 2016 | `self` | `_stats_grp_rename` | true | Qt-safe/default |
| 2017 | `hl` | `addWidget` | true | Qt-safe/default |
| 2019 | `del_btn` | `setFlat` | true | Qt-safe/default |
| 2020 | `del_btn.clicked` | `connect` | true | Qt-safe/default |
| 2020 | `self` | `_stats_grp_delete` | true | Qt-safe/default |
| 2021 | `hl` | `addWidget` | true | Qt-safe/default |
| 2024 | `self` | `_stats_select_grp` | true | Qt-safe/default |
| 2026 | `layout` | `addWidget` | true | Qt-safe/default |
| 2027 | `layout` | `addStretch` | true | Qt-safe/default |
| 2028 | `self` | `_stats_refresh_map` | true | Qt-safe/default |
| 2032 | `self` | `_stats_refresh_group_list` | true | Qt-safe/default |
| 2036 | `self._stats_groups` | `append` | true | Qt-safe/default |
| 2038 | `self` | `_stats_refresh_group_list` | true | Qt-safe/default |
| 2042 | `self._stats_groups` | `pop` | true | Qt-safe/default |
| 2045 | `self` | `_stats_refresh_group_list` | true | Qt-safe/default |
| 2054 | `self` | `_stats_refresh_group_list` | true | Qt-safe/default |
| 2057 | `self._stats_groups` | `clear` | true | Qt-safe/default |
| 2059 | `self` | `_stats_refresh_group_list` | true | Qt-safe/default |
| 2062 | `copy` | `deepcopy` | true | Qt-safe/default |
| 2062 | `self` | `_groups_from_rep_sets` | true | Qt-safe/default |
| 2064 | `self` | `_stats_refresh_group_list` | true | Qt-safe/default |
| 2087 | `self` | `_stats_write_result` | true | Qt-safe/default |
| 2093 | `self` | `_get_rows` | true | Qt-safe/default |
| 2094 | `row` | `get` | true | Qt-safe/default |
| 2096 | `all_tps` | `add` | true | Qt-safe/default |
| 2103 | `self._stats_tp_cb` | `setCurrentText` | true | Qt-safe/default |
| 2106 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 2107 | `self._stats_result_text` | `delete` | true | Qt-safe/default |
| 2109 | `self._stats_result_text` | `insert` | true | Qt-safe/default |
| 2110 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 2127 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2128 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2132 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2133 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2134 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2138 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2142 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2144 | `self._stats_fig` | `set_facecolor` | true | Qt-safe/default |
| 2148 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2152 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 2156 | `self._stats_canvas_widget` | `draw` | true | Qt-safe/default |
| 2223 | `self` | `_build_label_editor` | true | Qt-safe/default |
| 2266 | `self._rep_map_btns` | `items` | true | Qt-safe/default |
| 2268 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 2279 | `tok_active` | `get` | true | Qt-safe/default |
| 2282 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 2289 | `self` | `_mute_color` | true | Qt-safe/default |
| 2296 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 2308 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 2344 | `self._rep_map_btns` | `get` | true | Qt-safe/default |
| 2353 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 2367 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 2386 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 2387 | `self` | `_rep_refresh_map` | true | Qt-safe/default |
| 2392 | `dlg` | `setWindowTitle` | true | Qt-safe/default |
| 2393 | `dlg` | `setModal` | true | Qt-safe/default |
| 2395 | `v` | `addWidget` | true | Qt-safe/default |
| 2397 | `v` | `addWidget` | true | Qt-safe/default |
| 2398 | `v` | `addWidget` | true | Qt-safe/default |
| 2399 | `self._well_paths` | `keys` | true | Qt-safe/default |
| 2400 | `self` | `_parse_rc` | true | Qt-safe/default |
| 2402 | `v` | `addWidget` | true | Qt-safe/default |
| 2404 | `v` | `addLayout` | true | Qt-safe/default |
| 2406 | `ok_btn` | `setProperty` | true | Qt-safe/default |
| 2408 | `btn_row` | `addWidget` | true | Qt-safe/default |
| 2409 | `btn_row` | `addWidget` | true | Qt-safe/default |
| 2410 | `btn_row` | `addStretch` | true | Qt-safe/default |
| 2415 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 2417 | `name_edit.text()` | `strip` | true | Qt-safe/default |
| 2417 | `name_edit` | `text` | true | Qt-safe/default |
| 2418 | `self._rep_sets` | `append` | true | Qt-safe/default |
| 2420 | `dlg` | `accept` | true | Qt-safe/default |
| 2421 | `self` | `_rebuild_all` | true | Qt-safe/default |
| 2423 | `ok_btn.clicked` | `connect` | true | Qt-safe/default |
| 2424 | `cancel_btn.clicked` | `connect` | true | Qt-safe/default |
| 2425 | `dlg` | `exec` | true | Qt-safe/default |
| 2433 | `self` | `_rebuild_all` | true | Qt-safe/default |
| 2440 | `self._well_paths` | `keys` | true | Qt-safe/default |
| 2440 | `self` | `_parse_rc` | true | Qt-safe/default |
| 2443 | `dlg` | `setWindowTitle` | true | Qt-safe/default |
| 2444 | `dlg` | `setModal` | true | Qt-safe/default |
| 2446 | `v` | `addWidget` | true | Qt-safe/default |
| 2448 | `v` | `addWidget` | true | Qt-safe/default |
| 2450 | `v` | `addLayout` | true | Qt-safe/default |
| 2452 | `ok_btn` | `setProperty` | true | Qt-safe/default |
| 2454 | `btn_row` | `addWidget` | true | Qt-safe/default |
| 2455 | `btn_row` | `addWidget` | true | Qt-safe/default |
| 2456 | `btn_row` | `addStretch` | true | Qt-safe/default |
| 2460 | `dlg` | `accept` | true | Qt-safe/default |
| 2461 | `self` | `_rebuild_all` | true | Qt-safe/default |
| 2463 | `ok_btn.clicked` | `connect` | true | Qt-safe/default |
| 2464 | `cancel_btn.clicked` | `connect` | true | Qt-safe/default |
| 2465 | `dlg` | `exec` | true | Qt-safe/default |
| 2474 | `grp.members` | `remove` | true | Qt-safe/default |
| 2475 | `self._rep_sets` | `pop` | true | Qt-safe/default |
| 2478 | `self` | `_rebuild_all` | true | Qt-safe/default |
| 2483 | `QMessageBox` | `question` | true | Qt-safe/default |
| 2491 | `grp.members` | `clear` | true | Qt-safe/default |
| 2492 | `self._rep_sets` | `clear` | true | Qt-safe/default |
| 2494 | `self._rep_hidden` | `clear` | true | Qt-safe/default |
| 2495 | `self` | `_rebuild_all` | true | Qt-safe/default |
| 2557 | `self._well_labels` | `clear` | true | compat helper internals |
| 2558 | `self` | `_label_panel_refresh` | true | compat helper internals |
| 2559 | `self` | `_invalidate_stats_cache` | true | compat helper internals |
| 2568 | `nb` | `currentIndex` | true | compat helper internals |
| 2570 | `nb` | `tabText` | true | compat helper internals |
| 2574 | `nb` | `tab` | true | compat helper internals |
| 2574 | `nb` | `select` | true | compat helper internals |
| 2585 | `nb` | `select_by_text` | true | compat helper internals |
| 2591 | `nb` | `count` | true | compat helper internals |
| 2592 | `nb` | `tabText` | true | compat helper internals |
| 2593 | `nb` | `setCurrentIndex` | true | compat helper internals |
| 2604 | `widget` | `hide` | true | compat helper internals |
| 2606 | `widget` | `pack_forget` | true | compat helper internals |
| 2623 | `widget` | `show` | true | compat helper internals |
| 2639 | `widget` | `pack` | true | compat helper internals |
| 2648 | `widget` | `isVisible` | true | compat helper internals |
| 2653 | `widget` | `winfo_manager` | true | compat helper internals |
| 2664 | `widget` | `setText` | true | compat helper internals |
| 2666 | `widget` | `config` | true | compat helper internals |
| 2674 | `widget` | `clear` | true | compat helper internals |
| 2675 | `widget` | `addItems` | true | compat helper internals |
| 2677 | `widget` | `config` | true | compat helper internals |
| 2684 | `str(state)` | `lower` | true | compat helper internals |
| 2685 | `state_str` | `endswith` | true | compat helper internals |
| 2687 | `widget` | `setEnabled` | true | compat helper internals |
| 2689 | `widget` | `config` | true | compat helper internals |
| 2697 | `widget` | `configure` | true | compat helper internals |
| 2700 | `widget` | `setProperty` | true | compat helper internals |
| 2703 | `widget.style()` | `unpolish` | true | compat helper internals |
| 2703 | `widget` | `style` | true | compat helper internals |
| 2704 | `widget.style()` | `polish` | true | compat helper internals |
| 2704 | `widget` | `style` | true | compat helper internals |
| 2714 | `widget` | `config` | true | compat helper internals |
| 2723 | `kwargs` | `items` | true | compat helper internals |
| 2724 | `css_map` | `get` | true | compat helper internals |
| 2726 | `rules` | `append` | true | compat helper internals |
| 2728 | `widget` | `setStyleSheet` | true | compat helper internals |
| 2728 | `' '` | `join` | true | compat helper internals |
| 2738 | `widget` | `setCursor` | true | compat helper internals |
| 2740 | `widget` | `setCursor` | true | compat helper internals |
| 2742 | `widget` | `setCursor` | true | compat helper internals |
| 2744 | `widget` | `setCursor` | true | compat helper internals |
| 2746 | `widget` | `config` | true | compat helper internals |
| 2755 | `widget` | `setPixmap` | true | compat helper internals |
| 2755 | `image` | `toqpixmap` | true | compat helper internals |
| 2760 | `widget` | `configure` | true | compat helper internals |
| 2767 | `var` | `get` | true | compat helper internals |
| 2775 | `widget` | `currentText` | true | compat helper internals |
| 2780 | `widget` | `get` | true | compat helper internals |
| 2790 | `var` | `set` | true | compat helper internals |
| 2799 | `widget` | `setCurrentText` | true | compat helper internals |
| 2805 | `widget` | `set` | true | compat helper internals |
| 2814 | `widget` | `winfo_children` | true | compat helper internals |
| 2817 | `widget` | `findChildren` | true | compat helper internals |
| 2827 | `widget` | `winfo_width` | true | compat helper internals |
| 2830 | `widget` | `width` | true | compat helper internals |
| 2840 | `widget` | `winfo_height` | true | compat helper internals |
| 2843 | `widget` | `height` | true | compat helper internals |
| 2854 | `widget` | `winfo_exists` | true | compat helper internals |
| 2867 | `self` | `_active_tab_text` | true | compat helper internals |
| 2870 | `self` | `_rep_panel_refresh` | true | compat helper internals |
| 2871 | `self` | `_grp_panel_refresh` | true | compat helper internals |
| 2872 | `self` | `_label_panel_refresh` | true | compat helper internals |
| 2873 | `self` | `_rep_refresh_map` | true | compat helper internals |
| 2892 | `QTimer` | `singleShot` | true | compat helper internals |
| 2925 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 2926 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 2927 | `self` | `_bar_rebuild_groups_ui_now` | true | Qt-safe/default |
| 2928 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 2929 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 2930 | `self` | `_redraw` | true | Qt-safe/default |
| 2931 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 2932 | `self` | `_show_line_sidebar` | true | Qt-safe/default |
| 2941 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 2942 | `self` | `_bar_rebuild_groups_ui_now` | true | Qt-safe/default |
| 2943 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 2944 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 2945 | `self` | `_redraw` | true | Qt-safe/default |
| 2946 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 2947 | `self` | `_show_line_sidebar` | true | Qt-safe/default |
| 2955 | `self._bar_groups` | `append` | true | Qt-safe/default |
| 2958 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 2964 | `QMessageBox` | `question` | true | Qt-safe/default |
| 2970 | `self._bar_groups` | `clear` | true | Qt-safe/default |
| 2973 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 2979 | `self` | `_bar_rebuild_groups_ui` | true | Qt-safe/default |
| 2980 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 2988 | `self` | `_select_tab_by_text` | true | Qt-safe/default |
| 2989 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 2992 | `self._bar_groups[idx].replicates` | `clear` | true | Qt-safe/default |
| 2993 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3004 | `QMessageBox` | `information` | true | Qt-safe/default |
| 3009 | `dlg` | `setWindowTitle` | true | Qt-safe/default |
| 3010 | `dlg` | `setModal` | true | Qt-safe/default |
| 3012 | `v` | `addWidget` | true | Qt-safe/default |
| 3014 | `v` | `addWidget` | true | Qt-safe/default |
| 3015 | `v` | `addWidget` | true | Qt-safe/default |
| 3016 | `self` | `_parse_rc` | true | Qt-safe/default |
| 3018 | `v` | `addWidget` | true | Qt-safe/default |
| 3020 | `v` | `addLayout` | true | Qt-safe/default |
| 3022 | `add_btn` | `setProperty` | true | Qt-safe/default |
| 3024 | `btn_row` | `addWidget` | true | Qt-safe/default |
| 3025 | `btn_row` | `addWidget` | true | Qt-safe/default |
| 3026 | `btn_row` | `addStretch` | true | Qt-safe/default |
| 3031 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 3034 | `name_edit.text()` | `strip` | true | Qt-safe/default |
| 3034 | `name_edit` | `text` | true | Qt-safe/default |
| 3035 | `grp.replicates` | `append` | true | Qt-safe/default |
| 3036 | `dlg` | `accept` | true | Qt-safe/default |
| 3038 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3040 | `add_btn.clicked` | `connect` | true | Qt-safe/default |
| 3041 | `cancel_btn.clicked` | `connect` | true | Qt-safe/default |
| 3042 | `dlg` | `exec` | true | Qt-safe/default |
| 3049 | `grp.replicates` | `pop` | true | Qt-safe/default |
| 3052 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3057 | `self._bar_groups[idx].replicates` | `clear` | true | Qt-safe/default |
| 3059 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3065 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3068 | `self._bar_groups` | `pop` | true | Qt-safe/default |
| 3071 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3075 | `self._rep_hidden` | `clear` | true | Qt-safe/default |
| 3077 | `self._well_paths` | `keys` | true | Qt-safe/default |
| 3078 | `self` | `_bar_refresh_map` | true | Qt-safe/default |
| 3079 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 3083 | `self` | `_rep_sets_loaded` | true | Qt-safe/default |
| 3085 | `self._selected_wells` | `clear` | true | Qt-safe/default |
| 3086 | `self` | `_bar_refresh_map` | true | Qt-safe/default |
| 3087 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 3093 | `event.globalPosition()` | `toPoint` | true | Qt-safe/default |
| 3093 | `event` | `globalPosition` | true | Qt-safe/default |
| 3094 | `gp` | `x` | true | Qt-safe/default |
| 3094 | `gp` | `y` | true | Qt-safe/default |
| 3098 | `self._bar_map_btns` | `items` | true | Qt-safe/default |
| 3099 | `btn` | `isVisible` | true | explicit compatibility fallback path |
| 3099 | `btn` | `isEnabled` | true | explicit compatibility fallback path |
| 3100 | `btn` | `rect` | true | explicit compatibility fallback path |
| 3101 | `rect` | `center` | true | Qt-safe/default |
| 3102 | `btn` | `mapToGlobal` | true | explicit compatibility fallback path |
| 3103 | `centre_global` | `x` | true | Qt-safe/default |
| 3103 | `centre_global` | `y` | true | Qt-safe/default |
| 3107 | `self._vis_rubber_win` | `deleteLater` | true | Qt-safe/default |
| 3111 | `win` | `setAttribute` | true | Qt-safe/default |
| 3112 | `win` | `setWindowOpacity` | true | Qt-safe/default |
| 3113 | `win` | `setStyleSheet` | true | Qt-safe/default |
| 3114 | `win` | `setGeometry` | true | Qt-safe/default |
| 3115 | `win` | `show` | true | Qt-safe/default |
| 3116 | `win` | `raise_` | true | Qt-safe/default |
| 3123 | `event.globalPosition()` | `toPoint` | true | Qt-safe/default |
| 3123 | `event` | `globalPosition` | true | Qt-safe/default |
| 3124 | `gp` | `x` | true | Qt-safe/default |
| 3124 | `gp` | `y` | true | Qt-safe/default |
| 3129 | `self._vis_rubber_win` | `setGeometry` | true | Qt-safe/default |
| 3135 | `self._vis_rubber_win` | `deleteLater` | true | Qt-safe/default |
| 3151 | `event.globalPosition()` | `toPoint` | true | Qt-safe/default |
| 3151 | `event` | `globalPosition` | true | Qt-safe/default |
| 3152 | `gp` | `x` | true | Qt-safe/default |
| 3152 | `gp` | `y` | true | Qt-safe/default |
| 3159 | `btn_centres` | `items` | true | Qt-safe/default |
| 3162 | `inside_toks` | `add` | true | Qt-safe/default |
| 3167 | `self` | `_rep_sets_loaded` | true | Qt-safe/default |
| 3172 | `affected` | `add` | true | Qt-safe/default |
| 3181 | `self._rep_hidden` | `discard` | true | Qt-safe/default |
| 3183 | `self._rep_hidden` | `add` | true | Qt-safe/default |
| 3185 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 3186 | `self` | `_rep_refresh_map` | true | Qt-safe/default |
| 3187 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 3188 | `self` | `_bar_refresh_map` | true | Qt-safe/default |
| 3189 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 3190 | `self` | `_redraw` | true | Qt-safe/default |
| 3198 | `affected_groups` | `add` | true | Qt-safe/default |
| 3205 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3217 | `self` | `_rep_quick_pairs` | true | Qt-safe/default |
| 3226 | `self` | `_rep_quick_pairs` | true | Qt-safe/default |
| 3246 | `new_sets` | `extend` | true | Qt-safe/default |
| 3246 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3253 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3263 | `by_col[col]` | `append` | true | Qt-safe/default |
| 3267 | `new_sets` | `extend` | true | Qt-safe/default |
| 3275 | `new_sets` | `extend` | true | Qt-safe/default |
| 3275 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3282 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3292 | `by_row[row]` | `append` | true | Qt-safe/default |
| 3296 | `new_sets` | `extend` | true | Qt-safe/default |
| 3301 | `QMessageBox` | `question` | true | Qt-safe/default |
| 3310 | `grp.members` | `clear` | true | Qt-safe/default |
| 3313 | `self._rep_hidden` | `clear` | true | Qt-safe/default |
| 3314 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 3315 | `self` | `_rep_quick_refresh_ui` | true | Qt-safe/default |
| 3320 | `self._rep_quick_pair_dir_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3323 | `self._rep_quick_iter_order_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3326 | `self` | `_rep_quick_pairs` | true | Qt-safe/default |
| 3341 | `self` | `_rep_refresh_map` | true | Qt-safe/default |
| 3342 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 3343 | `self` | `_bar_refresh_map` | true | Qt-safe/default |
| 3346 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 3348 | `self` | `_rep_panel_refresh` | true | Qt-safe/default |
| 3353 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 3355 | `QTimer` | `singleShot` | true | Qt-safe/default |
| 3357 | `QTimer` | `singleShot` | true | Qt-safe/default |
| 3366 | `sets` | `append` | true | Qt-safe/default |
| 3370 | `sets` | `append` | true | Qt-safe/default |
| 3383 | `self._bar_groups` | `clear` | true | Qt-safe/default |
| 3395 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3396 | `self._bar_groups` | `append` | true | Qt-safe/default |
| 3404 | `_PLATE_COLS` | `index` | true | Qt-safe/default |
| 3406 | `loaded` | `append` | true | Qt-safe/default |
| 3409 | `pairs_in_col` | `extend` | true | Qt-safe/default |
| 3409 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3411 | `self._bar_groups` | `append` | true | Qt-safe/default |
| 3421 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3422 | `self._bar_groups` | `append` | true | Qt-safe/default |
| 3430 | `_PLATE_ROWS` | `index` | true | Qt-safe/default |
| 3432 | `loaded` | `append` | true | Qt-safe/default |
| 3435 | `pairs_in_row` | `extend` | true | Qt-safe/default |
| 3435 | `self` | `_make_replicate_pairs` | true | Qt-safe/default |
| 3437 | `self._bar_groups` | `append` | true | Qt-safe/default |
| 3441 | `self` | `_bar_rebuild_groups_ui_now` | true | Qt-safe/default |
| 3442 | `QTimer` | `singleShot` | true | Qt-safe/default |
| 3447 | `self._bar_quick_pair_dir_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3450 | `self._bar_quick_iter_order_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3453 | `self` | `_bar_quick_groups` | true | Qt-safe/default |
| 3462 | `self` | `_bar_quick_groups` | true | Qt-safe/default |
| 3471 | `self` | `_bar_quick_groups` | true | Qt-safe/default |
| 3495 | `self._rep_sets` | `clear` | true | Qt-safe/default |
| 3496 | `self._bar_groups` | `clear` | true | Qt-safe/default |
| 3499 | `self._rep_hidden` | `clear` | true | Qt-safe/default |
| 3511 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 3519 | `QFileDialog` | `getSaveFileName` | true | Qt-safe/default |
| 3528 | `json` | `dump` | true | Qt-safe/default |
| 3528 | `self` | `_bar_groups_to_dict` | true | Qt-safe/default |
| 3529 | `_logger` | `info` | true | Qt-safe/default |
| 3531 | `QMessageBox` | `critical` | true | Qt-safe/default |
| 3537 | `QFileDialog` | `getOpenFileName` | true | Qt-safe/default |
| 3546 | `json` | `load` | true | Qt-safe/default |
| 3550 | `QMessageBox` | `critical` | true | Qt-safe/default |
| 3556 | `QMessageBox` | `question` | true | Qt-safe/default |
| 3564 | `self` | `_bar_groups_from_dict` | true | Qt-safe/default |
| 3565 | `self` | `_bar_rebuild_groups` | true | Qt-safe/default |
| 3566 | `_logger` | `info` | true | Qt-safe/default |
| 3586 | `event.globalPosition()` | `toPoint` | true | Qt-safe/default |
| 3586 | `event` | `globalPosition` | true | Qt-safe/default |
| 3587 | `gp` | `x` | true | Qt-safe/default |
| 3587 | `gp` | `y` | true | Qt-safe/default |
| 3589 | `event.widget` | `winfo_rootx` | true | explicit compatibility fallback path |
| 3590 | `event.widget` | `winfo_rooty` | true | explicit compatibility fallback path |
| 3592 | `event.widget` | `winfo_containing` | true | explicit compatibility fallback path |
| 3594 | `QApplication` | `widgetAt` | true | Qt-safe/default |
| 3595 | `self._bar_map_btns` | `items` | true | Qt-safe/default |
| 3609 | `self` | `_sb_press` | true | Qt-safe/default |
| 3612 | `self` | `_sb_drag` | true | Qt-safe/default |
| 3615 | `self` | `_sb_release` | true | Qt-safe/default |
| 3618 | `self` | `_sb_on_rep_change` | true | Qt-safe/default |
| 3637 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 3643 | `self` | `_bar_refresh_map` | true | Qt-safe/default |
| 3673 | `self._mon_tophat_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3674 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 3675 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3676 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 3677 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 3678 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 3679 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 3680 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3682 | `self._mon_tophat_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3683 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 3684 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3685 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 3686 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 3687 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 3688 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 3689 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3702 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3705 | `self` | `_widget_children` | true | Qt-safe/default |
| 3706 | `w` | `destroy` | true | Qt-safe/default |
| 3707 | `self._montage_photos` | `clear` | true | Qt-safe/default |
| 3717 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3720 | `self._preview_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3722 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3726 | `_debug_flags` | `movie_montage_debug_enabled` | true | Qt-safe/default |
| 3727 | `_debug_flags` | `movie_montage_load_debug_enabled` | true | Qt-safe/default |
| 3733 | `self._preview_fluor` | `items` | true | Qt-safe/default |
| 3738 | `tophat_refs` | `items` | true | Qt-safe/default |
| 3741 | `raw_by_tp` | `keys` | true | Qt-safe/default |
| 3742 | `tophat_by_tp` | `keys` | true | Qt-safe/default |
| 3744 | `ordered_tps` | `append` | true | Qt-safe/default |
| 3745 | `tophat_by_tp` | `get` | true | Qt-safe/default |
| 3745 | `raw_by_tp` | `get` | true | Qt-safe/default |
| 3749 | `self._preview_overlay` | `items` | true | Qt-safe/default |
| 3756 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3760 | `_debug_flags` | `debug_with_source` | true | Qt-safe/default |
| 3770 | `_debug_flags` | `debug_with_source` | true | Qt-safe/default |
| 3777 | `_debug_flags` | `debug_with_source` | true | Qt-safe/default |
| 3784 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3785 | `self` | `update_idletasks` | true | Qt-safe/default |
| 3788 | `ov_map` | `get` | true | Qt-safe/default |
| 3802 | `_debug_flags` | `debug_with_source` | true | Qt-safe/default |
| 3814 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 3815 | `self` | `_montage_auto_lut` | true | Qt-safe/default |
| 3816 | `self` | `_update_tophat_controls` | true | Qt-safe/default |
| 3817 | `self` | `_draw_montage_thumbs` | true | Qt-safe/default |
| 3823 | `widget` | `bind` | true | Qt-safe/default |
| 3828 | `self` | `_widget_children` | true | Qt-safe/default |
| 3829 | `w` | `destroy` | true | Qt-safe/default |
| 3830 | `self._montage_photos` | `clear` | true | Qt-safe/default |
| 3835 | `self._mon_lmin_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3839 | `self._mon_lmax_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3850 | `self._mon_tophat_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3860 | `self` | `_widget_width` | true | Qt-safe/default |
| 3869 | `self._montage_zoom_lbl` | `setText` | true | Qt-safe/default |
| 3871 | `self._montage_inner` | `layout` | true | Qt-safe/default |
| 3874 | `grid` | `setContentsMargins` | true | Qt-safe/default |
| 3875 | `grid` | `setSpacing` | true | Qt-safe/default |
| 3877 | `self._active_image_channel` | `upper` | true | Qt-safe/default |
| 3878 | `channel_row_lbl` | `setObjectName` | true | Qt-safe/default |
| 3879 | `channel_row_lbl` | `setAlignment` | true | Qt-safe/default |
| 3880 | `grid` | `addWidget` | true | Qt-safe/default |
| 3882 | `overlay_row_lbl` | `setObjectName` | true | Qt-safe/default |
| 3883 | `overlay_row_lbl` | `setAlignment` | true | Qt-safe/default |
| 3884 | `grid` | `addWidget` | true | Qt-safe/default |
| 3888 | `ev` | `modifiers` | true | Qt-safe/default |
| 3889 | `self` | `_on_montage_shift_wheel` | true | Qt-safe/default |
| 3891 | `self` | `_on_montage_wheel` | true | Qt-safe/default |
| 3895 | `self` | `_on_montage_fluor_motion` | true | Qt-safe/default |
| 3898 | `self._montage_tooltip` | `hide` | true | Qt-safe/default |
| 3901 | `w` | `setMouseTracking` | true | Qt-safe/default |
| 3910 | `col_layout` | `setContentsMargins` | true | Qt-safe/default |
| 3911 | `col_layout` | `setSpacing` | true | Qt-safe/default |
| 3912 | `grid` | `addWidget` | true | Qt-safe/default |
| 3915 | `tp_lbl` | `setObjectName` | true | Qt-safe/default |
| 3916 | `tp_lbl` | `setAlignment` | true | Qt-safe/default |
| 3917 | `col_layout` | `addWidget` | true | Qt-safe/default |
| 3921 | `fluor_cell` | `setFrameShape` | true | Qt-safe/default |
| 3923 | `fluor_cell_layout` | `setContentsMargins` | true | Qt-safe/default |
| 3924 | `col_layout` | `addWidget` | true | Qt-safe/default |
| 3928 | `self._montage_photos` | `append` | true | Qt-safe/default |
| 3930 | `lbl_fluor` | `setPixmap` | true | Qt-safe/default |
| 3931 | `lbl_fluor` | `setCursor` | true | Qt-safe/default |
| 3937 | `fluor_cell_layout` | `addWidget` | true | Qt-safe/default |
| 3940 | `self._active_image_channel` | `upper` | true | Qt-safe/default |
| 3941 | `miss` | `setObjectName` | true | Qt-safe/default |
| 3942 | `miss` | `setAlignment` | true | Qt-safe/default |
| 3943 | `fluor_cell_layout` | `addWidget` | true | Qt-safe/default |
| 3946 | `self._mon_tophat_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 3957 | `th_lbl` | `setStyleSheet` | true | Qt-safe/default |
| 3958 | `th_lbl` | `setAlignment` | true | Qt-safe/default |
| 3959 | `th_lbl` | `show` | true | Qt-safe/default |
| 3960 | `self._montage_th_overlay_lbls` | `append` | true | Qt-safe/default |
| 3962 | `self._montage_th_overlay_lbls` | `append` | true | Qt-safe/default |
| 3965 | `ov_cell` | `setFrameShape` | true | Qt-safe/default |
| 3967 | `ov_cell_layout` | `setContentsMargins` | true | Qt-safe/default |
| 3968 | `col_layout` | `addWidget` | true | Qt-safe/default |
| 3971 | `self._montage_photos` | `append` | true | Qt-safe/default |
| 3973 | `lbl_ov` | `setPixmap` | true | Qt-safe/default |
| 3974 | `ov_cell_layout` | `addWidget` | true | Qt-safe/default |
| 3978 | `miss` | `setObjectName` | true | Qt-safe/default |
| 3979 | `miss` | `setAlignment` | true | Qt-safe/default |
| 3980 | `ov_cell_layout` | `addWidget` | true | Qt-safe/default |
| 3982 | `self._montage_status` | `setText` | true | Qt-safe/default |
| 4034 | `QApplication` | `instance` | true | Qt-safe/default |
| 4036 | `app` | `setStyleSheet` | true | Qt-safe/default |
| 4044 | `self` | `_apply_theme` | true | Qt-safe/default |
| 4047 | `self` | `_rep_panel_refresh` | true | Qt-safe/default |
| 4049 | `self` | `_grp_panel_refresh` | true | Qt-safe/default |
| 4051 | `self` | `_stats_refresh_colors` | true | Qt-safe/default |
| 4054 | `self` | `_refresh_sidebar_map_now` | true | Qt-safe/default |
| 4060 | `QFileDialog` | `getExistingDirectory` | true | Qt-safe/default |
| 4063 | `QTimer` | `singleShot` | true | Qt-safe/default |
| 4063 | `self` | `_load_path` | true | Qt-safe/default |
| 4082 | `self._tmp_dir` | `exists` | true | Qt-safe/default |
| 4083 | `shutil` | `rmtree` | true | Qt-safe/default |
| 4087 | `self` | `_cleanup_tmp` | true | Qt-safe/default |
| 4089 | `self._tk_root` | `destroy` | true | Qt-safe/default |
| 4091 | `self` | `destroy` | true | Qt-safe/default |
| 4096 | `re` | `search` | true | Qt-safe/default |
| 4099 | `m.group(1)` | `upper` | true | Qt-safe/default |
| 4099 | `m` | `group` | true | Qt-safe/default |
| 4099 | `m` | `group` | true | Qt-safe/default |
| 4114 | `self._cache` | `values` | true | Qt-safe/default |
| 4116 | `row` | `get` | true | Qt-safe/default |
| 4118 | `math` | `isnan` | true | Qt-safe/default |
| 4119 | `row` | `get` | true | Qt-safe/default |
| 4122 | `all_tps` | `add` | true | Qt-safe/default |
| 4124 | `pipeline_info` | `get` | true | Qt-safe/default |
| 4127 | `all_tps` | `add` | true | Qt-safe/default |
| 4133 | `str(value or '')` | `strip` | true | Qt-safe/default |
| 4142 | `self._cache` | `values` | true | Qt-safe/default |
| 4144 | `row` | `get` | true | Qt-safe/default |
| 4146 | `all_fovs` | `add` | true | Qt-safe/default |
| 4148 | `pipeline_info` | `get` | true | Qt-safe/default |
| 4151 | `all_fovs` | `add` | true | Qt-safe/default |
| 4153 | `all_fovs` | `add` | true | Qt-safe/default |
| 4171 | `hex_color` | `lstrip` | true | Qt-safe/default |
| 4180 | `self` | `_rep_sets_active` | true | Qt-safe/default |
| 4187 | `QTimer` | `singleShot` | true | Qt-safe/default |
| 4216 | `self` | `_mute_color` | true | Qt-safe/default |
| 4221 | `self._sidebar_btns` | `items` | true | Qt-safe/default |
| 4223 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 4238 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 4251 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 4256 | `self` | `_mute_color` | true | Qt-safe/default |
| 4264 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 4276 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 4281 | `self` | `_mute_color` | true | Qt-safe/default |
| 4288 | `self` | `_style_plate_button` | true | Qt-safe/default |
| 4301 | `self` | `_rep_sets_loaded` | true | Qt-safe/default |
| 4302 | `self` | `_rep_sets_active` | true | Qt-safe/default |
| 4311 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4317 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4323 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4345 | `str(state)` | `lower` | true | Qt-safe/default |
| 4346 | `str(relief)` | `lower` | true | Qt-safe/default |
| 4347 | `state_str` | `endswith` | true | Qt-safe/default |
| 4348 | `relief_str` | `endswith` | true | Qt-safe/default |
| 4350 | `btn` | `setEnabled` | true | explicit compatibility fallback path |
| 4352 | `btn` | `setCursor` | true | explicit compatibility fallback path |
| 4359 | `btn` | `setStyleSheet` | true | explicit compatibility fallback path |
| 4360 | `'\n'` | `join` | true | Qt-safe/default |
| 4387 | `btn` | `config` | true | explicit compatibility fallback path |
| 4445 | `self` | `_rep_sets_loaded` | true | Qt-safe/default |
| 4469 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 4470 | `self` | `_redraw` | true | Qt-safe/default |
| 4471 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 4493 | `self` | `_get_rows` | true | Qt-safe/default |
| 4498 | `str(tok).strip()` | `lower` | true | Qt-safe/default |
| 4498 | `str(tok)` | `strip` | true | Qt-safe/default |
| 4499 | `self._pipeline_info` | `get` | true | Qt-safe/default |
| 4500 | `str(tok)` | `strip` | true | Qt-safe/default |
| 4506 | `str(self._pipeline_info.get('nuclear_token', '') or '').strip()` | `lower` | true | Qt-safe/default |
| 4506 | `str(self._pipeline_info.get('nuclear_token', '') or '')` | `strip` | true | Qt-safe/default |
| 4506 | `self._pipeline_info` | `get` | true | Qt-safe/default |
| 4520 | `self` | `_update_channel_selector` | true | Qt-safe/default |
| 4534 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 4536 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 4541 | `self` | `_update_bar_tp_menu` | true | Qt-safe/default |
| 4543 | `self` | `_stats_update_tp_menu` | true | Qt-safe/default |
| 4546 | `self` | `_get_rows` | true | Qt-safe/default |
| 4557 | `self._cell_gating_tab` | `_load_cell_areas` | true | Qt-safe/default |
| 4559 | `self._cell_gating_tab` | `_load_threshold_frac_on` | true | Qt-safe/default |
| 4574 | `self` | `_recalculate_threshold` | true | Qt-safe/default |
| 4575 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 4576 | `self` | `_redraw` | true | Qt-safe/default |
| 4578 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 4579 | `channel` | `upper` | true | Qt-safe/default |
| 4581 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4583 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4587 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 4589 | `_logger` | `debug` | true | Qt-safe/default |
| 4601 | `self` | `_refresh_review_image` | true | Qt-safe/default |
| 4603 | `_logger` | `debug` | true | Qt-safe/default |
| 4611 | `channel` | `upper` | true | Qt-safe/default |
| 4613 | `self._montage_chan_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4615 | `self._review_image_chan_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4617 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4619 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4620 | `self._review_image_lut_by_channel` | `get` | true | Qt-safe/default |
| 4622 | `self._review_lut_min_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4623 | `self._review_lut_max_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4628 | `_logger` | `debug` | true | Qt-safe/default |
| 4632 | `self` | `_update_preview` | true | Qt-safe/default |
| 4634 | `_logger` | `debug` | true | Qt-safe/default |
| 4642 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 4643 | `_logger` | `debug` | true | Qt-safe/default |
| 4644 | `self._get_var_value('_review_image_chan_var', '', '_review_image_chan_cb')` | `strip` | true | Qt-safe/default |
| 4644 | `self` | `_get_var_value` | true | Qt-safe/default |
| 4645 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 4646 | `_logger` | `debug` | true | Qt-safe/default |
| 4651 | `self` | `_set_active_image_channel` | true | Qt-safe/default |
| 4651 | `selected_ui_value` | `lower` | true | Qt-safe/default |
| 4655 | `self` | `_set_active_channel` | true | Qt-safe/default |
| 4655 | `self._plot_chan_var.get()` | `lower` | true | Qt-safe/default |
| 4655 | `self._plot_chan_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4659 | `self._get_var_value('_montage_chan_var', '', '_chan_cb_preview')` | `strip` | true | Qt-safe/default |
| 4659 | `self` | `_get_var_value` | true | Qt-safe/default |
| 4660 | `_debug_flags` | `movie_montage_debug_enabled` | true | Qt-safe/default |
| 4661 | `_logger` | `debug` | true | Qt-safe/default |
| 4666 | `self` | `_set_active_image_channel` | true | Qt-safe/default |
| 4666 | `selected_ui_value` | `lower` | true | Qt-safe/default |
| 4670 | `self._metric_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4672 | `self` | `_set_active_metric` | true | Qt-safe/default |
| 4683 | `self._metric_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4684 | `self` | `_recalculate_threshold` | true | Qt-safe/default |
| 4685 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 4686 | `self` | `_redraw` | true | Qt-safe/default |
| 4688 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 4692 | `ch` | `upper` | true | Qt-safe/default |
| 4697 | `montage_chans` | `append` | true | Qt-safe/default |
| 4698 | `ch` | `upper` | true | Qt-safe/default |
| 4699 | `ch` | `upper` | true | Qt-safe/default |
| 4704 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 4706 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 4708 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 4709 | `self._active_channel` | `upper` | true | Qt-safe/default |
| 4721 | `self` | `_get_var_value` | true | Qt-safe/default |
| 4722 | `self` | `_set_var_value` | true | Qt-safe/default |
| 4725 | `self._active_image_channel` | `upper` | true | Qt-safe/default |
| 4726 | `self` | `_get_var_value` | true | Qt-safe/default |
| 4727 | `self` | `_get_var_value` | true | Qt-safe/default |
| 4728 | `self` | `_set_var_value` | true | Qt-safe/default |
| 4729 | `self` | `_set_var_value` | true | Qt-safe/default |
| 4735 | `self` | `_set_active_image_channel` | true | Qt-safe/default |
| 4735 | `fallback_image_label` | `lower` | true | Qt-safe/default |
| 4740 | `self` | `_set_active_channel` | true | Qt-safe/default |
| 4740 | `plot_label` | `lower` | true | Qt-safe/default |
| 4748 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 4750 | `self._chan_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4752 | `self._chan_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4754 | `self._chan_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4757 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 4758 | `self._use_sem` | `set` | true | Qt-safe/default |
| 4758 | `self._use_sem` | `get` | true | Qt-safe/default |
| 4759 | `self._use_sem` | `get` | true | Qt-safe/default |
| 4760 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4761 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 4762 | `self` | `_redraw` | true | Qt-safe/default |
| 4763 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 4764 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 4780 | `self` | `_parse_rc` | true | Qt-safe/default |
| 4791 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 4794 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4796 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4799 | `self._preview_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4804 | `self._review_image_tp_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4807 | `self` | `_widget_children` | true | Qt-safe/default |
| 4808 | `w` | `destroy` | true | Qt-safe/default |
| 4809 | `self._montage_photos` | `clear` | true | Qt-safe/default |
| 4810 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4812 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4814 | `_logger` | `debug` | true | Qt-safe/default |
| 4819 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4822 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4825 | `str(self._active_image_channel or '').strip()` | `lower` | true | Qt-safe/default |
| 4825 | `str(self._active_image_channel or '')` | `strip` | true | Qt-safe/default |
| 4827 | `_logger` | `debug` | true | Qt-safe/default |
| 4841 | `_logger` | `exception` | true | Qt-safe/default |
| 4848 | `_logger` | `debug` | true | Qt-safe/default |
| 4862 | `self` | `_update_tophat_controls` | true | Qt-safe/default |
| 4865 | `str(value or '')` | `strip` | true | Qt-safe/default |
| 4883 | `refs` | `keys` | true | Qt-safe/default |
| 4890 | `_logger` | `debug` | true | Qt-safe/default |
| 4893 | `self._preview_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4899 | `self._preview_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4903 | `_logger` | `warning` | true | Qt-safe/default |
| 4905 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4910 | `self._preview_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4912 | `self._preview_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4914 | `self._preview_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4918 | `self._preview_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4920 | `self._preview_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4922 | `self` | `_refresh_preview_montage` | true | Qt-safe/default |
| 4924 | `_logger` | `debug` | true | Qt-safe/default |
| 4925 | `self` | `_refresh_review_image` | true | Qt-safe/default |
| 4928 | `self` | `_refresh_preview_montage` | true | Qt-safe/default |
| 4931 | `str(value or '')` | `strip` | true | Qt-safe/default |
| 4941 | `str(v or '')` | `strip` | true | Qt-safe/default |
| 4951 | `row` | `get` | true | Qt-safe/default |
| 4952 | `str(k)` | `lower` | true | Qt-safe/default |
| 4952 | `row` | `items` | true | Qt-safe/default |
| 4954 | `name` | `lower` | true | Qt-safe/default |
| 4960 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 4967 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 4969 | `_debug_flags` | `review_image_load_debug_enabled` | true | Qt-safe/default |
| 4973 | `_logger` | `debug` | true | Qt-safe/default |
| 4976 | `str(v or '')` | `strip` | true | Qt-safe/default |
| 4984 | `str(self._preview_fov_var.get() or '')` | `strip` | true | Qt-safe/default |
| 4984 | `self._preview_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 4987 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 4989 | `_logger` | `debug` | true | Qt-safe/default |
| 5004 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5005 | `self._preview_fluor` | `keys` | true | Qt-safe/default |
| 5006 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5012 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5013 | `getattr(self, '_pipeline_info', {}) or {}` | `get` | true | Qt-safe/default |
| 5014 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5021 | `_logger` | `debug` | true | Qt-safe/default |
| 5029 | `_logger` | `debug` | true | Qt-safe/default |
| 5037 | `self._preview_fluor` | `items` | true | Qt-safe/default |
| 5045 | `_logger` | `debug` | true | Qt-safe/default |
| 5052 | `_logger` | `debug` | true | Qt-safe/default |
| 5056 | `getattr(self, '_preview_tophat_fluor', {})` | `items` | true | Qt-safe/default |
| 5064 | `_logger` | `debug` | true | Qt-safe/default |
| 5071 | `self._review_image_tp_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5072 | `self._review_image_tp_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5073 | `str(self._review_image_tp_var.get() or '')` | `strip` | true | Qt-safe/default |
| 5073 | `self._review_image_tp_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5074 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5076 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 5078 | `_logger` | `debug` | true | Qt-safe/default |
| 5107 | `self._preview_fluor` | `keys` | true | Qt-safe/default |
| 5108 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5112 | `getattr(self, '_preview_tophat_fluor', {})` | `keys` | true | Qt-safe/default |
| 5113 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5115 | `_logger` | `debug` | true | Qt-safe/default |
| 5129 | `_debug_flags` | `debug_with_source` | true | Qt-safe/default |
| 5137 | `_debug_flags` | `debug_with_source` | true | Qt-safe/default |
| 5146 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 5148 | `_logger` | `debug` | true | Qt-safe/default |
| 5154 | `str(getattr(fluor_ref, 'name', '')).lower()` | `endswith` | true | Qt-safe/default |
| 5154 | `str(getattr(fluor_ref, 'name', ''))` | `lower` | true | Qt-safe/default |
| 5159 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 5162 | `_np` | `asarray` | true | Qt-safe/default |
| 5164 | `_np` | `unique` | true | Qt-safe/default |
| 5166 | `self` | `_review_load_rows` | true | Qt-safe/default |
| 5168 | `self` | `_review_row_keys` | true | Qt-safe/default |
| 5175 | `str(row.get('Included', '1'))` | `strip` | true | Qt-safe/default |
| 5175 | `row` | `get` | true | Qt-safe/default |
| 5180 | `_logger` | `debug` | true | Qt-safe/default |
| 5181 | `self` | `_draw_review_image` | true | Qt-safe/default |
| 5190 | `str(self._active_image_channel or '')` | `lower` | true | Qt-safe/default |
| 5193 | `self._review_lut_min_var.get()` | `strip` | true | Qt-safe/default |
| 5193 | `self._review_lut_min_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5194 | `self._review_lut_max_var.get()` | `strip` | true | Qt-safe/default |
| 5194 | `self._review_lut_max_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5200 | `self._review_image_lut_by_channel` | `get` | true | Qt-safe/default |
| 5203 | `arr` | `min` | true | Qt-safe/default |
| 5204 | `arr` | `max` | true | Qt-safe/default |
| 5214 | `_np` | `asarray` | true | Qt-safe/default |
| 5215 | `arr_np` | `min` | true | Qt-safe/default |
| 5216 | `arr_np` | `max` | true | Qt-safe/default |
| 5219 | `str(self._active_image_channel or '')` | `lower` | true | Qt-safe/default |
| 5221 | `self._review_lut_min_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5222 | `self._review_lut_max_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5224 | `self` | `_refresh_review_image` | true | Qt-safe/default |
| 5230 | `self` | `_review_image_resolve_lut` | true | Qt-safe/default |
| 5230 | `_np` | `asarray` | true | Qt-safe/default |
| 5232 | `self._review_lut_min_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5233 | `self._review_lut_max_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5235 | `self` | `_refresh_review_image` | true | Qt-safe/default |
| 5246 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 5247 | `_logger` | `debug` | true | Qt-safe/default |
| 5253 | `_np` | `asarray` | true | Qt-safe/default |
| 5255 | `_np` | `asarray` | true | Qt-safe/default |
| 5257 | `arr` | `min` | true | Qt-safe/default |
| 5257 | `arr` | `max` | true | Qt-safe/default |
| 5260 | `str(self._active_image_channel or '')` | `lower` | true | Qt-safe/default |
| 5262 | `self` | `_review_image_resolve_lut` | true | Qt-safe/default |
| 5264 | `self._review_lut_chan_lbl` | `setText` | true | Qt-safe/default |
| 5264 | `self._active_image_channel` | `upper` | true | Qt-safe/default |
| 5266 | `self._review_lut_min_edit` | `setText` | true | Qt-safe/default |
| 5267 | `self._review_lut_max_edit` | `setText` | true | Qt-safe/default |
| 5268 | `(_np.clip(arr, lo, hi) - lo) / (hi - lo) * 255` | `astype` | true | Qt-safe/default |
| 5268 | `_np` | `clip` | true | Qt-safe/default |
| 5269 | `_np` | `dstack` | true | Qt-safe/default |
| 5271 | `_np.rint(m)` | `astype` | true | Qt-safe/default |
| 5271 | `_np` | `rint` | true | Qt-safe/default |
| 5272 | `_np` | `pad` | true | Qt-safe/default |
| 5280 | `_np` | `zeros` | true | Qt-safe/default |
| 5281 | `include_by_nid` | `items` | true | Qt-safe/default |
| 5285 | `_np` | `array` | true | Qt-safe/default |
| 5289 | `_np` | `array` | true | Qt-safe/default |
| 5291 | `_PILImage` | `fromarray` | true | Qt-safe/default |
| 5297 | `self` | `_render_review_image_display` | true | Qt-safe/default |
| 5301 | `lbl` | `setMouseTracking` | true | Qt-safe/default |
| 5304 | `self` | `_on_review_image_hover` | true | Qt-safe/default |
| 5307 | `self._review_image_tooltip` | `hide` | true | Qt-safe/default |
| 5311 | `self` | `_on_review_image_wheel` | true | Qt-safe/default |
| 5313 | `self` | `_on_review_image_press` | true | Qt-safe/default |
| 5315 | `ev` | `buttons` | true | Qt-safe/default |
| 5316 | `self` | `_on_review_image_drag` | true | Qt-safe/default |
| 5320 | `self` | `_on_review_image_release` | true | Qt-safe/default |
| 5327 | `lbl` | `setCursor` | true | Qt-safe/default |
| 5329 | `self._review_image_status` | `setText` | true | Qt-safe/default |
| 5330 | `self._active_image_channel` | `upper` | true | Qt-safe/default |
| 5332 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 5333 | `_logger` | `debug` | true | Qt-safe/default |
| 5344 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 5345 | `_logger` | `debug` | true | Qt-safe/default |
| 5349 | `self` | `_widget_width` | true | Qt-safe/default |
| 5350 | `self` | `_widget_height` | true | Qt-safe/default |
| 5354 | `img` | `resize` | true | Qt-safe/default |
| 5355 | `_PILImageTk` | `PhotoImage` | true | Qt-safe/default |
| 5356 | `self` | `_set_widget_image` | true | Qt-safe/default |
| 5360 | `self._review_image_canvas` | `coords` | true | Qt-safe/default |
| 5365 | `_debug_flags` | `review_image_channel_switch_debug_enabled` | true | Qt-safe/default |
| 5366 | `_logger` | `debug` | true | Qt-safe/default |
| 5381 | `self` | `_render_review_image_display` | true | Qt-safe/default |
| 5387 | `self` | `_render_review_image_display` | true | Qt-safe/default |
| 5395 | `self` | `_review_image_zoom_step` | true | Qt-safe/default |
| 5413 | `self` | `_render_review_image_display` | true | Qt-safe/default |
| 5421 | `self` | `_on_review_image_click` | true | Qt-safe/default |
| 5426 | `self` | `_widget_width` | true | Qt-safe/default |
| 5427 | `self` | `_widget_height` | true | Qt-safe/default |
| 5432 | `self._active_image_channel` | `upper` | true | Qt-safe/default |
| 5444 | `self` | `_set_widget_cursor` | true | Qt-safe/default |
| 5446 | `self` | `_set_status` | true | Qt-safe/default |
| 5448 | `self` | `_set_status` | true | Qt-safe/default |
| 5451 | `self` | `_set_review_image_include_mode` | true | Qt-safe/default |
| 5456 | `self` | `_review_row_keys` | true | Qt-safe/default |
| 5460 | `str(included)` | `strip` | true | Qt-safe/default |
| 5464 | `self` | `_refresh_review_csv_rows` | true | Qt-safe/default |
| 5465 | `self` | `_refresh_review_image` | true | Qt-safe/default |
| 5469 | `self` | `_render_review_image_display` | true | Qt-safe/default |
| 5478 | `_np` | `where` | true | Qt-safe/default |
| 5481 | `xs` | `mean` | true | Qt-safe/default |
| 5482 | `ys` | `mean` | true | Qt-safe/default |
| 5488 | `self` | `_widget_width` | true | Qt-safe/default |
| 5489 | `self` | `_widget_height` | true | Qt-safe/default |
| 5497 | `self` | `_render_review_image_display` | true | Qt-safe/default |
| 5518 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 5520 | `self` | `_select_tab_by_text` | true | Qt-safe/default |
| 5522 | `self` | `_batch_export_set_mode` | true | Qt-safe/default |
| 5543 | `self` | `_apply_export_style_if_ready` | true | Qt-safe/default |
| 5549 | `self` | `_active_tab_text` | true | Qt-safe/default |
| 5553 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5554 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5555 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5556 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5557 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5560 | `self` | `_sync_preview_well_for_image_tabs` | true | Qt-safe/default |
| 5561 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5562 | `self` | `_refresh_preview_picker` | true | Qt-safe/default |
| 5563 | `self` | `_update_preview` | true | Qt-safe/default |
| 5566 | `self` | `_sync_preview_well_for_image_tabs` | true | Qt-safe/default |
| 5567 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5568 | `self` | `_refresh_preview_picker` | true | Qt-safe/default |
| 5569 | `self` | `_update_preview` | true | Qt-safe/default |
| 5570 | `self` | `_refresh_review_image` | true | Qt-safe/default |
| 5573 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5574 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 5577 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5580 | `self` | `_stats_sync_from_app` | true | Qt-safe/default |
| 5582 | `self` | `_stats_update_tp_menu` | true | Qt-safe/default |
| 5587 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5588 | `self` | `_groups_centre_refresh` | true | Qt-safe/default |
| 5590 | `getattr(self, '_batch_export_inline_state', {})` | `get` | true | Qt-safe/default |
| 5591 | `self` | `_batch_export_set_mode` | true | Qt-safe/default |
| 5594 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5595 | `self` | `_widget_is_visible` | true | Qt-safe/default |
| 5596 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5597 | `self` | `_widget_is_visible` | true | Qt-safe/default |
| 5598 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5599 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 5600 | `self` | `_refresh_review_csv` | true | Qt-safe/default |
| 5603 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5605 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5607 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 5611 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 5613 | `self._smfish_tab` | `sync_from_app` | true | Qt-safe/default |
| 5617 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5618 | `self` | `_widget_is_visible` | true | Qt-safe/default |
| 5619 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5620 | `self` | `_widget_is_visible` | true | Qt-safe/default |
| 5621 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 5622 | `self` | `_refresh_sidebar_map` | true | Qt-safe/default |
| 5624 | `self` | `_update_bar_tp_menu` | true | Qt-safe/default |
| 5625 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 5627 | `self` | `_update_scatter_menus` | true | Qt-safe/default |
| 5628 | `self` | `_redraw_scatter` | true | Qt-safe/default |
| 5630 | `self` | `_update_scatter_menus` | true | Qt-safe/default |
| 5631 | `self` | `_redraw_scatter_agg` | true | Qt-safe/default |
| 5633 | `self` | `_redraw` | true | Qt-safe/default |
| 5635 | `self` | `_run_tab_switch_smoke_checks` | true | Qt-safe/default |
| 5662 | `self._well_paths` | `keys` | true | Qt-safe/default |
| 5685 | `_logger` | `warning` | true | Qt-safe/default |
| 5693 | `_logger` | `warning` | true | Qt-safe/default |
| 5711 | `self._review_well_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5714 | `self._review_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5715 | `self._review_tp_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5716 | `self` | `_refresh_review_csv_rows` | true | Qt-safe/default |
| 5717 | `self._review_csv_msg` | `set` | true | Qt-safe/default |
| 5720 | `self._review_well_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5720 | `', '` | `join` | true | Qt-safe/default |
| 5723 | `rows` | `extend` | true | Qt-safe/default |
| 5723 | `self` | `_review_load_rows` | true | Qt-safe/default |
| 5727 | `self._review_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5728 | `self._review_tp_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5729 | `self` | `_refresh_review_csv_rows` | true | Qt-safe/default |
| 5730 | `self._review_csv_msg` | `set` | true | Qt-safe/default |
| 5734 | `str(r.get('fov', r.get('FOV', '')))` | `strip` | true | Qt-safe/default |
| 5734 | `r` | `get` | true | Qt-safe/default |
| 5734 | `r` | `get` | true | Qt-safe/default |
| 5736 | `str(r.get('fov', r.get('FOV', '')))` | `strip` | true | Qt-safe/default |
| 5736 | `r` | `get` | true | Qt-safe/default |
| 5736 | `r` | `get` | true | Qt-safe/default |
| 5741 | `str(row.get('timepoint', row.get('tp', row.get('time', ''))))` | `strip` | true | Qt-safe/default |
| 5741 | `row` | `get` | true | Qt-safe/default |
| 5741 | `row` | `get` | true | Qt-safe/default |
| 5741 | `row` | `get` | true | Qt-safe/default |
| 5742 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5745 | `seen_tps` | `add` | true | Qt-safe/default |
| 5746 | `tps` | `append` | true | Qt-safe/default |
| 5747 | `tps` | `sort` | true | Qt-safe/default |
| 5750 | `self._review_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5751 | `self._review_fov_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5752 | `self._review_tp_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5753 | `self._review_tp_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5754 | `self` | `_refresh_review_csv_rows` | true | Qt-safe/default |
| 5760 | `table` | `get_children` | true | Qt-safe/default |
| 5761 | `table` | `delete` | true | Qt-safe/default |
| 5767 | `rows` | `extend` | true | Qt-safe/default |
| 5767 | `self` | `_review_load_rows` | true | Qt-safe/default |
| 5770 | `str(v or '')` | `strip` | true | Qt-safe/default |
| 5778 | `self._review_fov_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5779 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5779 | `self._review_tp_var` | `get` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 5782 | `row` | `get` | true | Qt-safe/default |
| 5782 | `row` | `get` | true | Qt-safe/default |
| 5783 | `self` | `_norm_timepoint` | true | Qt-safe/default |
| 5783 | `row` | `get` | true | Qt-safe/default |
| 5783 | `row` | `get` | true | Qt-safe/default |
| 5783 | `row` | `get` | true | Qt-safe/default |
| 5788 | `filtered` | `append` | true | Qt-safe/default |
| 5791 | `_logger` | `warning` | true | Qt-safe/default |
| 5798 | `self._review_csv_msg` | `set` | true | Qt-safe/default |
| 5803 | `self._review_csv_msg` | `set` | true | Qt-safe/default |
| 5808 | `ctx` | `get` | true | Qt-safe/default |
| 5808 | `ctx` | `get` | true | Qt-safe/default |
| 5808 | `ctx` | `get` | true | Qt-safe/default |
| 5808 | `ctx` | `get` | true | Qt-safe/default |
| 5811 | `self` | `_set_status` | true | Qt-safe/default |
| 5815 | `filtered[0]` | `keys` | true | Qt-safe/default |
| 5818 | `table` | `heading` | true | Qt-safe/default |
| 5819 | `table` | `column` | true | Qt-safe/default |
| 5821 | `table` | `insert` | true | Qt-safe/default |
| 5821 | `row` | `get` | true | Qt-safe/default |
| 5822 | `self._review_csv_msg` | `set` | true | Qt-safe/default |
| 5828 | `self` | `_get_rows` | true | Qt-safe/default |
| 5829 | `self` | `_extract_well_token` | true | Qt-safe/default |
| 5831 | `row` | `setdefault` | true | Qt-safe/default |
| 5835 | `str(row.get('included', ''))` | `strip` | true | Qt-safe/default |
| 5835 | `row` | `get` | true | Qt-safe/default |
| 5837 | `row` | `pop` | true | Qt-safe/default |
| 5838 | `self` | `_review_row_keys` | true | Qt-safe/default |
| 5841 | `self._review_included_overrides` | `get` | true | Qt-safe/default |
| 5859 | `self` | `_set_var_value` | true | Qt-safe/default |
| 5867 | `all_tps` | `add` | true | Qt-safe/default |
| 5872 | `self` | `_get_var_value` | true | Qt-safe/default |
| 5875 | `self` | `_set_var_value` | true | Qt-safe/default |
| 5877 | `self` | `_set_var_value` | true | Qt-safe/default |
| 5879 | `self` | `_set_var_value` | true | Qt-safe/default |
| 5893 | `fig.canvas` | `get_renderer` | true | Qt-safe/default |
| 5896 | `ax` | `get_window_extent` | true | Qt-safe/default |
| 5900 | `ax.transData` | `inverted` | true | Qt-safe/default |
| 5901 | `inv` | `transform` | true | Qt-safe/default |
| 5920 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 5921 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 5925 | `self` | `_bar_pixel_to_data_x` | true | Qt-safe/default |
| 5928 | `self` | `_bar_current_keys` | true | Qt-safe/default |
| 5932 | `self` | `_bar_idx_at_x` | true | Qt-safe/default |
| 5933 | `self._bar_drag_state` | `update` | true | Qt-safe/default |
| 5940 | `self` | `_bar_pixel_to_data_x` | true | Qt-safe/default |
| 5943 | `self` | `_bar_current_keys` | true | Qt-safe/default |
| 5947 | `self` | `_bar_idx_at_x` | true | Qt-safe/default |
| 5956 | `ln` | `remove` | true | Qt-safe/default |
| 5961 | `ax` | `axvline` | true | Qt-safe/default |
| 5964 | `self._bar_canvas` | `draw_idle` | true | Qt-safe/default |
| 5977 | `ln` | `remove` | true | Qt-safe/default |
| 5982 | `self._bar_canvas` | `draw_idle` | true | Qt-safe/default |
| 5985 | `self` | `_bar_current_keys` | true | Qt-safe/default |
| 5987 | `self._bar_canvas` | `draw_idle` | true | Qt-safe/default |
| 5990 | `keys` | `pop` | true | Qt-safe/default |
| 5991 | `keys` | `insert` | true | Qt-safe/default |
| 5993 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 5994 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 5998 | `self._bar_log_scale` | `set` | true | Qt-safe/default |
| 5998 | `self._bar_log_scale` | `get` | true | Qt-safe/default |
| 5999 | `self._bar_log_scale` | `get` | true | Qt-safe/default |
| 6000 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 6001 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 6014 | `self._bar_swarm` | `set` | true | Qt-safe/default |
| 6014 | `self._bar_swarm` | `get` | true | Qt-safe/default |
| 6015 | `self._bar_swarm` | `get` | true | Qt-safe/default |
| 6016 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 6017 | `self._bar_violin` | `get` | true | Qt-safe/default |
| 6019 | `self._bar_violin` | `set` | true | Qt-safe/default |
| 6020 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 6021 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 6022 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 6026 | `self._bar_violin` | `set` | true | Qt-safe/default |
| 6026 | `self._bar_violin` | `get` | true | Qt-safe/default |
| 6027 | `self._bar_violin` | `get` | true | Qt-safe/default |
| 6028 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 6029 | `self` | `_set_widget_state` | true | Qt-safe/default |
| 6030 | `self` | `_set_widget_palette` | true | Qt-safe/default |
| 6031 | `self._bar_swarm` | `get` | true | Qt-safe/default |
| 6033 | `self._bar_swarm` | `set` | true | Qt-safe/default |
| 6034 | `self` | `_set_widget_style` | true | Qt-safe/default |
| 6035 | `self` | `_redraw_bars` | true | Qt-safe/default |
| 6059 | `ax_mean` | `text` | true | Qt-safe/default |
| 6066 | `self._violin_bw` | `get` | true | Qt-safe/default |
| 6073 | `self` | `_get_rows` | true | Qt-safe/default |
| 6079 | `row` | `get` | true | Qt-safe/default |
| 6093 | `vals` | `append` | true | Qt-safe/default |
| 6095 | `frac_vals` | `append` | true | Qt-safe/default |
| 6100 | `ax_mean` | `scatter` | true | Qt-safe/default |
| 6103 | `np_local` | `array` | true | Qt-safe/default |
| 6105 | `arr` | `min` | true | Qt-safe/default |
| 6105 | `arr` | `max` | true | Qt-safe/default |
| 6107 | `np_local` | `linspace` | true | Qt-safe/default |
| 6110 | `density` | `max` | true | Qt-safe/default |
| 6115 | `ax_mean` | `fill_betweenx` | true | Qt-safe/default |
| 6117 | `ax_mean` | `plot` | true | Qt-safe/default |
| 6118 | `ax_mean` | `plot` | true | Qt-safe/default |
| 6121 | `np_local` | `median` | true | Qt-safe/default |
| 6122 | `ax_mean` | `hlines` | true | Qt-safe/default |
| 6124 | `ax_mean` | `hlines` | true | Qt-safe/default |
| 6129 | `math` | `isnan` | true | Qt-safe/default |
| 6130 | `ax_frac` | `scatter` | true | Qt-safe/default |
| 6132 | `ax_frac` | `scatter` | true | Qt-safe/default |
| 6136 | `ax_mean` | `axhline` | true | Qt-safe/default |
| 6137 | `ax_frac` | `axhline` | true | Qt-safe/default |
| 6139 | `ax` | `set_xticks` | true | Qt-safe/default |
| 6140 | `ax` | `set_xticklabels` | true | Qt-safe/default |
| 6144 | `ax` | `set_xlim` | true | Qt-safe/default |
| 6145 | `ax_frac` | `set_ylim` | true | Qt-safe/default |
| 6146 | `ax_frac` | `set_ylabel` | true | Qt-safe/default |
| 6147 | `ax_mean` | `set_title` | true | Qt-safe/default |
| 6148 | `self._active_channel` | `upper` | true | Qt-safe/default |
| 6150 | `ax_frac` | `set_title` | true | Qt-safe/default |
| 6179 | `self` | `_get_rows` | true | Qt-safe/default |
| 6187 | `row` | `get` | true | Qt-safe/default |
| 6189 | `math` | `isnan` | true | Qt-safe/default |
| 6191 | `row` | `get` | true | Qt-safe/default |
| 6201 | `cell_vals` | `append` | true | Qt-safe/default |
| 6208 | `ax_mean` | `scatter` | true | Qt-safe/default |
| 6212 | `ax_mean` | `plot` | true | Qt-safe/default |
| 6217 | `ax_mean` | `scatter` | true | Qt-safe/default |
| 6221 | `ax_frac` | `scatter` | true | Qt-safe/default |
| 6224 | `ax_frac` | `scatter` | true | Qt-safe/default |
| 6227 | `ax_mean` | `axhline` | true | Qt-safe/default |
| 6229 | `ax_frac` | `axhline` | true | Qt-safe/default |
| 6232 | `ax` | `set_xticks` | true | Qt-safe/default |
| 6233 | `ax` | `set_xticklabels` | true | Qt-safe/default |
| 6237 | `ax` | `set_xlim` | true | Qt-safe/default |
| 6238 | `ax_frac` | `set_ylim` | true | Qt-safe/default |
| 6239 | `ax_frac` | `set_ylabel` | true | Qt-safe/default |
| 6240 | `ax_mean` | `set_title` | true | Qt-safe/default |
| 6241 | `self._active_channel` | `upper` | true | Qt-safe/default |
| 6243 | `ax_frac` | `set_title` | true | Qt-safe/default |
| 6251 | `ax_mean` | `cla` | true | Qt-safe/default |
| 6252 | `ax_frac` | `cla` | true | Qt-safe/default |
| 6254 | `self._use_sem` | `get` | true | Qt-safe/default |
| 6256 | `self` | `_get_thresh_frac_on` | true | Qt-safe/default |
| 6258 | `self` | `_rep_sets_active` | true | Qt-safe/default |
| 6259 | `self` | `_selected_bar_wells` | true | Qt-safe/default |
| 6261 | `self._active_channel` | `upper` | true | Qt-safe/default |
| 6268 | `ax_frac` | `set_ylim` | true | Qt-safe/default |
| 6271 | `self` | `_draw_bar_empty_state` | true | Qt-safe/default |
| 6274 | `self` | `_resolve_bar_timepoint` | true | Qt-safe/default |
| 6276 | `self` | `_draw_bar_empty_state` | true | Qt-safe/default |
| 6280 | `self` | `_draw_per_cell_bar_mode` | true | Qt-safe/default |
| 6289 | `self` | `_draw_grouped_bar_mode` | true | Qt-safe/default |
| 6299 | `self` | `_apply_export_style_if_ready` | true | Qt-safe/default |
| 6306 | `self` | `_parse_rc` | true | Qt-safe/default |
| 6311 | `ax` | `text` | true | Qt-safe/default |
| 6321 | `ax` | `set_axis_off` | true | Qt-safe/default |
| 6322 | `self._bar_canvas` | `draw_idle` | true | Qt-safe/default |
| 6325 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6343 | `self._bar_violin` | `get` | true | Qt-safe/default |
| 6343 | `self._bar_swarm` | `get` | true | Qt-safe/default |
| 6346 | `self` | `_bar_current_keys` | true | Qt-safe/default |
| 6354 | `rset_by_name` | `get` | true | Qt-safe/default |
| 6357 | `all_set_idx` | `get` | true | Qt-safe/default |
| 6361 | `plot_wells` | `append` | true | Qt-safe/default |
| 6362 | `plot_colors` | `append` | true | Qt-safe/default |
| 6363 | `plot_labels` | `append` | true | Qt-safe/default |
| 6363 | `self` | `_well_display_label` | true | Qt-safe/default |
| 6367 | `self` | `_well_display_label` | true | Qt-safe/default |
| 6368 | `_debug_flags` | `review_bar_debug_enabled` | true | Qt-safe/default |
| 6369 | `self._bar_violin` | `get` | true | Qt-safe/default |
| 6372 | `self._bar_violin` | `get` | true | Qt-safe/default |
| 6373 | `self` | `_draw_violin` | true | Qt-safe/default |
| 6375 | `self` | `_draw_beeswarm` | true | Qt-safe/default |
| 6384 | `self._bar_log_scale` | `get` | true | Qt-safe/default |
| 6386 | `self` | `_apply_bar_ylims` | true | Qt-safe/default |
| 6389 | `self._bar_log_scale` | `get` | true | Qt-safe/default |
| 6389 | `self._bar_swarm` | `get` | true | Qt-safe/default |
| 6391 | `self._bar_canvas` | `draw_idle` | true | Qt-safe/default |
| 6406 | `self` | `_collect_bar_items` | true | Qt-safe/default |
| 6411 | `all_set_idx` | `get` | true | Qt-safe/default |
| 6415 | `self` | `_bar_current_keys` | true | Qt-safe/default |
| 6416 | `by_key` | `get` | true | Qt-safe/default |
| 6419 | `self` | `_compute_rep_stats` | true | Qt-safe/default |
| 6420 | `self` | `_replicate_display_label` | true | Qt-safe/default |
| 6422 | `ordered` | `append` | true | Qt-safe/default |
| 6430 | `math` | `isnan` | true | Qt-safe/default |
| 6431 | `color_by_key` | `get` | true | Qt-safe/default |
| 6438 | `self` | `_bar_current_keys` | true | Qt-safe/default |
| 6440 | `self` | `_bar_well_display_label` | true | Qt-safe/default |
| 6456 | `ax_frac` | `set_ylabel` | true | Qt-safe/default |
| 6457 | `self._active_channel` | `upper` | true | Qt-safe/default |
| 6458 | `ax_mean` | `set_title` | true | Qt-safe/default |
| 6465 | `ax_frac` | `set_title` | true | Qt-safe/default |
| 6472 | `self` | `_apply_bar_ylims` | true | Qt-safe/default |
| 6473 | `self._bar_canvas` | `draw_idle` | true | Qt-safe/default |
| 6480 | `self._well_labels` | `get` | true | Qt-safe/default |
| 6484 | `self` | `_well_display_label` | true | Qt-safe/default |
| 6485 | `re` | `match` | true | Qt-safe/default |
| 6496 | `str(getattr(rset, 'name', '') or '')` | `strip` | true | Qt-safe/default |
| 6501 | `re` | `match` | true | Qt-safe/default |
| 6510 | `self` | `_well_display_label` | true | Qt-safe/default |
| 6514 | `','` | `join` | true | Qt-safe/default |
| 6515 | `','` | `join` | true | Qt-safe/default |
| 6524 | `self` | `_rep_sets_loaded` | true | Qt-safe/default |
| 6543 | `self` | `_get_cell_area_threshold` | true | Qt-safe/default |
| 6544 | `self` | `_get_all_fluor_gates` | true | Qt-safe/default |
| 6546 | `fluor_gates` | `items` | true | Qt-safe/default |
| 6555 | `self` | `_get_rows` | true | Qt-safe/default |
| 6563 | `math` | `isnan` | true | Qt-safe/default |
| 6563 | `well_means` | `append` | true | Qt-safe/default |
| 6564 | `math` | `isnan` | true | Qt-safe/default |
| 6564 | `well_fracs` | `append` | true | Qt-safe/default |
| 6567 | `statistics` | `mean` | true | Qt-safe/default |
| 6569 | `statistics` | `pstdev` | true | Qt-safe/default |
| 6570 | `math` | `sqrt` | true | Qt-safe/default |
| 6575 | `statistics` | `mean` | true | Qt-safe/default |
| 6577 | `statistics` | `pstdev` | true | Qt-safe/default |
| 6578 | `math` | `sqrt` | true | Qt-safe/default |
| 6606 | `self` | `_get_cell_area_threshold` | true | Qt-safe/default |
| 6607 | `self` | `_get_all_fluor_gates` | true | Qt-safe/default |
| 6609 | `fluor_gates` | `items` | true | Qt-safe/default |
| 6616 | `grp` | `replicate_sets` | true | Qt-safe/default |
| 6622 | `self` | `_get_rows` | true | Qt-safe/default |
| 6630 | `math` | `isnan` | true | Qt-safe/default |
| 6630 | `set_means` | `append` | true | Qt-safe/default |
| 6631 | `math` | `isnan` | true | Qt-safe/default |
| 6631 | `set_fracs` | `append` | true | Qt-safe/default |
| 6633 | `rep_means` | `append` | true | Qt-safe/default |
| 6633 | `statistics` | `mean` | true | Qt-safe/default |
| 6635 | `rep_fracs` | `append` | true | Qt-safe/default |
| 6635 | `statistics` | `mean` | true | Qt-safe/default |
| 6638 | `statistics` | `mean` | true | Qt-safe/default |
| 6640 | `statistics` | `pstdev` | true | Qt-safe/default |
| 6641 | `math` | `sqrt` | true | Qt-safe/default |
| 6646 | `statistics` | `mean` | true | Qt-safe/default |
| 6648 | `statistics` | `pstdev` | true | Qt-safe/default |
| 6649 | `math` | `sqrt` | true | Qt-safe/default |
| 6686 | `self._use_sem` | `get` | true | Qt-safe/default |
| 6688 | `self` | `_get_thresh_frac_on` | true | Qt-safe/default |
| 6691 | `fig` | `add_subplot` | true | Qt-safe/default |
| 6692 | `fig` | `add_subplot` | true | Qt-safe/default |
| 6693 | `fig` | `subplots_adjust` | true | Qt-safe/default |
| 6695 | `self._active_channel` | `upper` | true | Qt-safe/default |
| 6699 | `ax_frac` | `set_ylim` | true | Qt-safe/default |
| 6701 | `self` | `_collect_bar_items` | true | Qt-safe/default |
| 6703 | `self` | `_rep_sets_active` | true | Qt-safe/default |
| 6704 | `self` | `_replicate_display_label` | true | Qt-safe/default |
| 6711 | `self` | `_bar_well_display_label` | true | Qt-safe/default |
| 6737 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 6739 | `self` | `_select_tab_by_text` | true | Qt-safe/default |
| 6741 | `self` | `_batch_export_set_mode` | true | Qt-safe/default |
| 6746 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 6748 | `self` | `_select_tab_by_text` | true | Qt-safe/default |
| 6750 | `self` | `_batch_export_set_mode` | true | Qt-safe/default |
| 6755 | `QMessageBox` | `warning` | true | Qt-safe/default |
| 6757 | `self` | `_select_tab_by_text` | true | Qt-safe/default |
| 6759 | `self` | `_batch_export_set_mode` | true | Qt-safe/default |
| 6798 | `mapping` | `get` | true | Qt-safe/default |
| 6800 | `self` | `_set_status` | true | Qt-safe/default |
| 6804 | `self` | `_set_status` | true | Qt-safe/default |
| 6814 | `entry` | `endswith` | true | Qt-safe/default |
| 6826 | `scatter_ch_options` | `append` | true | Qt-safe/default |
| 6828 | `scatter_ch_options` | `append` | true | Qt-safe/default |
| 6830 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 6831 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 6834 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6835 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6837 | `self` | `_set_var_value` | true | Qt-safe/default |
| 6839 | `self` | `_set_var_value` | true | Qt-safe/default |
| 6848 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 6850 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6852 | `self` | `_set_var_value` | true | Qt-safe/default |
| 6858 | `statistics` | `append` | true | Qt-safe/default |
| 6858 | `ch` | `upper` | true | Qt-safe/default |
| 6859 | `statistics` | `append` | true | Qt-safe/default |
| 6859 | `ch` | `upper` | true | Qt-safe/default |
| 6861 | `statistics` | `append` | true | Qt-safe/default |
| 6861 | `ch` | `upper` | true | Qt-safe/default |
| 6863 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 6864 | `self` | `_set_widget_values` | true | Qt-safe/default |
| 6867 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6868 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6870 | `self` | `_set_var_value` | true | Qt-safe/default |
| 6872 | `self` | `_set_var_value` | true | Qt-safe/default |
| 6880 | `self._scatter_agg_tp_selections` | `items` | true | Qt-safe/default |
| 6881 | `self._scatter_agg_tp_selections` | `clear` | true | Qt-safe/default |
| 6889 | `self` | `_update_tp_selection_display` | true | Qt-safe/default |
| 6893 | `self._scatter_agg_tp_selections` | `values` | true | Qt-safe/default |
| 6897 | `self._scatter_agg_tp_label` | `setText` | true | Qt-safe/default |
| 6902 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6903 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6904 | `self` | `_get_var_value` | true | Qt-safe/default |
| 6910 | `ch_x_entry` | `split` | true | Qt-safe/default |
| 6911 | `ch_y_entry` | `split` | true | Qt-safe/default |
| 6913 | `self` | `_get_cell_area_threshold` | true | Qt-safe/default |
| 6914 | `self` | `_get_fluor_gate` | true | Qt-safe/default |
| 6915 | `self` | `_get_fluor_gate` | true | Qt-safe/default |
| 6918 | `self` | `_col_for_scatter_entry` | true | Qt-safe/default |
| 6919 | `self` | `_col_for_scatter_entry` | true | Qt-safe/default |
| 6931 | `self` | `_apply_export_style_if_ready` | true | Qt-safe/default |
| 6943 | `interaction_cache` | `get` | true | Qt-safe/default |
| 6963 | `self` | `_open_scatter_cell_viewer` | true | Qt-safe/default |
| 6966 | `self` | `_set_status` | true | Qt-safe/default |
| 6975 | `interaction_cache` | `get` | true | Qt-safe/default |
| 6995 | `self` | `_set_status` | true | Qt-safe/default |
| 6997 | `self` | `_set_status` | true | Qt-safe/default |
| 7012 | `self` | `_widget_exists` | true | Qt-safe/default |
| 7022 | `self._scatter_cell_viewer` | `update_cell` | true | Qt-safe/default |
| 7023 | `self._scatter_cell_viewer` | `lift` | true | Qt-safe/default |
| 7024 | `self._scatter_cell_viewer` | `focus` | true | Qt-safe/default |
| 7041 | `self` | `_get_var_value` | true | Qt-safe/default |
| 7042 | `self` | `_get_var_value` | true | Qt-safe/default |
| 7047 | `self._ax_scatter_agg` | `clear` | true | Qt-safe/default |
| 7048 | `self._ax_scatter_agg` | `text` | true | Qt-safe/default |
| 7056 | `self._scatter_agg_canvas` | `draw` | true | Qt-safe/default |
| 7060 | `self._scatter_agg_tp_selections` | `items` | true | Qt-safe/default |
| 7061 | `var` | `get` | true | Qt-safe/default |
| 7064 | `selected_timepoints` | `append` | true | Qt-safe/default |
| 7070 | `self._ax_scatter_agg` | `clear` | true | Qt-safe/default |
| 7071 | `self._ax_scatter_agg` | `text` | true | Qt-safe/default |
| 7079 | `self._scatter_agg_canvas` | `draw` | true | Qt-safe/default |
| 7095 | `self` | `_apply_export_style_if_ready` | true | Qt-safe/default |
| 7128 | `self._line_ax_cdf` | `get_xlim` | true | Qt-safe/default |
| 7134 | `self` | `_set_status` | true | Qt-safe/default |
| 7146 | `ax_map` | `get` | true | Qt-safe/default |
| 7150 | `clicked_ax` | `get_legend` | true | Qt-safe/default |
| 7152 | `leg` | `set_visible` | true | Qt-safe/default |
| 7153 | `self._line_canvas` | `draw_idle` | true | Qt-safe/default |
| 7155 | `self` | `_set_status` | true | Qt-safe/default |
| 7165 | `self._line_ax_cdf` | `get_xlim` | true | Qt-safe/default |
| 7171 | `self._entry_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 7172 | `self` | `_invalidate_stats_cache` | true | Qt-safe/default |
| 7174 | `self` | `_redraw` | true | Qt-safe/default |
| 7186 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 7191 | `self._progress_bar` | `setRange` | true | Qt-safe/default |
| 7192 | `self._progress_bar` | `setValue` | true | Qt-safe/default |
| 7193 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 7195 | `self._progress_bar` | `setMaximum` | true | Qt-safe/default |
| 7196 | `self._progress_bar` | `setValue` | true | Qt-safe/default |
| 7197 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 7201 | `progress_bar` | `config` | true | explicit compatibility fallback path |
| 7202 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 7204 | `self` | `_set_status` | true | Qt-safe/default |
| 7205 | `self` | `update` | true | Qt-safe/default |
| 7210 | `self._progress_bar` | `setValue` | true | Qt-safe/default |
| 7212 | `self._progress_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 7214 | `self` | `_set_status` | true | Qt-safe/default |
| 7215 | `self` | `update` | true | Qt-safe/default |
| 7220 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 7221 | `self._progress_bar` | `setValue` | true | Qt-safe/default |
| 7223 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 7225 | `self._progress_var` | `set` | true | direct app *_var access with __getattr__/_CompatVar fallback |
| 7230 | `self` | `_show_compat_widget` | true | Qt-safe/default |
| 7231 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 7233 | `self` | `_hide_compat_widget` | true | Qt-safe/default |
| 7234 | `self` | `_set_widget_text` | true | Qt-safe/default |
| 7238 | `self._log_text` | `clear` | true | Qt-safe/default |
| 7254 | `argparse` | `ArgumentParser` | true | Qt-safe/default |
| 7256 | `ap` | `add_argument` | true | Qt-safe/default |
| 7258 | `ap` | `parse_args` | true | Qt-safe/default |
| 7259 | `QApplication` | `instance` | true | Qt-safe/default |
| 7261 | `win` | `setWindowTitle` | true | Qt-safe/default |
| 7263 | `win` | `setCentralWidget` | true | Qt-safe/default |
| 7264 | `win` | `resize` | true | Qt-safe/default |
| 7265 | `win` | `show` | true | Qt-safe/default |
| 7266 | `qapp` | `exec` | true | Qt-safe/default |
