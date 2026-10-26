# Kahra Studio · `.github`

Bu depo, [Kahra Studio](https://github.com/Kahra-Studio) organizasyon sayfasında görünen profili barındırır.

- `profile/README.md`: organizasyon sayfasındaki metin
- `profile/assets/`: açık ve koyu tema için üretilmiş SVG görseller
- `scripts/build_assets.py`: görselleri üreten betik

## Görselleri güncellemek

Hizmetler, vaka çalışmaları ve künye satırındaki sayılar `scripts/build_assets.py` içinde tutulur. Değiştirdikten sonra:

```bash
python -m pip install uharfbuzz fonttools
python scripts/build_assets.py
```

Betik Lexend ve JetBrains Mono fontlarını ilk çalıştırmada `.cache/fonts` altına indirir ve metinleri vektör yola çevirir. GitHub, README'deki SVG'lerin font yüklemesine izin vermediği için tipografi ancak bu şekilde sitedekiyle aynı görünür.
