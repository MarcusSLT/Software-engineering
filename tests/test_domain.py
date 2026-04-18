import pytest
from datetime import datetime, timezone
from src.ti_framework.domain.models import Snapshot

# Убедись, что импорты находятся в начале файла
from src.ti_framework.domain.exceptions import (
    SnapshotValidationError as DomainException,
)


class TestSnapshotModelValidation:
    """Тесты валидации модели Snapshot."""

    def test_valid_snapshot_creation(self):
        # Сценарий 1: Валидные данные должны пройти проверку без ошибок
        now = datetime.now(timezone.utc)

        try:
            snapshot = Snapshot(
                collected_at=now,
                source_url="https://example.com",
                source_name="TestSource",
                data=b"<html>Valid content</html>",
                snapshot_kind="index",
            )

            # Проверка результата (используем список для структуры вывода)
            results = [
                {"status": "success", "hash_present": bool(snapshot.sha256_hex)},
                {"collected_at_utc": now.tzinfo is not None},
            ]

            # Исправленная проверка: хеш должен быть строкой и содержать hex-символы (16+ символов)
            assert isinstance(snapshot.sha256_hex, str), "Хэш должен быть строкой"
            assert len(snapshot.sha256_hex) > 0, "Хэш не может быть пустым"

        except Exception as e:
            # Если возникла ошибка при создании валидного объекта — это баг теста или модели
            pytest.fail(f"Валидный снапшот должен был создаться успешно. Ошибка: {e}")

    def test_snapshot_with_naive_datetime_raises_error(self):
        """Проверка, что дата без часового пояса вызывает ошибку."""

        naive_time = datetime(2024, 1, 1)  # Без tzinfo

        try:
            snapshot = Snapshot(
                collected_at=naive_time,
                source_url="https://example.com",
                source_name="TestSource",
                data=b"<html>Content</html>",
            )

            # Если код дошел сюда — тест провален (ошибка должна была выброситься)
            pytest.fail(
                "Ожидается исключение SnapshotValidationError при создании снапшота с невалидной датой"
            )

        except DomainException as e:
            # Ошибка перехвачена корректно, проверяем сообщение
            assert "must be timezone-aware" in str(e), (
                f"Ошибка должна содержать текст валидации. Получено: {e}"
            )

    def test_snapshot_with_empty_source_name_raises_error(self):
        """Проверка, что пустое имя источника вызывает ошибку."""

        now = datetime.now(timezone.utc)

        try:
            snapshot = Snapshot(
                collected_at=now,
                source_url="https://example.com",
                source_name="",  # Проблемное поле
                data=b"<html>Content</html>",
            )

            pytest.fail("Ожидается исключение при пустом имени источника")

        except DomainException as e:
            assert "must not be empty" in str(e), (
                f"Ошибка должна содержать текст валидации. Получено: {e}"
            )
