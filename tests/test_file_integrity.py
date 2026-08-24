import hashlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from benchwork.file_integrity import FILE_HASH_CHUNK_BYTES, file_sigil


class FileIntegrityTest(unittest.TestCase):
    def test_file_sigil_uses_bounded_reads(self) -> None:
        payload = b"x" * (FILE_HASH_CHUNK_BYTES * 2 + 17)
        reads: list[int] = []

        class BoundedReader(io.BytesIO):
            def read(self, size: int = -1) -> bytes:
                reads.append(size)
                return super().read(size)

        with patch.object(Path, "open", return_value=BoundedReader(payload)):
            sigil = file_sigil(Path("ignored.bin"))

        self.assertEqual(sigil, "sha256:" + hashlib.sha256(payload).hexdigest())
        self.assertGreater(len(reads), 1)
        self.assertTrue(all(size == FILE_HASH_CHUNK_BYTES for size in reads))


if __name__ == "__main__":
    unittest.main()
