from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from backend.app.services.dwg_converter import DwgConversionError, convert_dwg_to_image


class TestDwgConverter:
    def test_missing_oda_path_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.app.services.dwg_converter.ODA_CONVERTER_PATH", None)
        monkeypatch.setattr("backend.app.services.dwg_converter.shutil.which", lambda _: None)

        dwg_path = tmp_path / "sample.dwg"
        dwg_path.write_bytes(b"AC1021 fake")

        with pytest.raises(DwgConversionError, match="not configured"):
            convert_dwg_to_image(dwg_path)

    @patch("backend.app.services.dwg_converter.rasterize_dxf_to_image")
    @patch("backend.app.services.dwg_converter.convert_dwg_to_dxf")
    @patch("backend.app.services.dwg_converter._resolve_oda_converter_path")
    def test_convert_dwg_to_image_success(
        self,
        mock_resolve: MagicMock,
        mock_convert_dxf: MagicMock,
        mock_rasterize: MagicMock,
        tmp_path: Path,
    ) -> None:
        dwg_path = tmp_path / "sample.dwg"
        dwg_path.write_bytes(b"AC1021 fake")
        dxf_path = tmp_path / "sample.dxf"
        dxf_path.write_text("0\nSECTION", encoding="ascii")

        mock_resolve.return_value = tmp_path / "ODAFileConverter.exe"
        mock_convert_dxf.return_value = (dxf_path, tmp_path)
        mock_rasterize.return_value = Image.new("RGB", (100, 100), color="white")

        image = convert_dwg_to_image(dwg_path)
        assert image.size == (100, 100)
        mock_convert_dxf.assert_called_once_with(dwg_path)
        mock_rasterize.assert_called_once()
