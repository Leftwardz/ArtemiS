"""Work search path in queue operations."""

from unittest.mock import patch

from app.services.work_queue_service import search_work_for_queue


class _FakeDb:
    pass


def test_not_found_reports_resolved_search_path():
    resolved = r'C:\Workorders\PADRAO'

    with patch('app.services.work_queue_service.resolve_work_search_path', return_value=resolved):
        with patch('app.services.work_queue_service.os.path.exists', return_value=True):
            with patch('app.services.work_queue_service.find_work_in_directory', return_value=None):
                result = search_work_for_queue(
                    'MISSING',
                    r'C:\Workorders',
                    'PADRAO',
                    is_remake=False,
                    skip_remake_screen=False,
                    queued_paths=[],
                    defined_paper_size=None,
                    defined_color=None,
                    db=_FakeDb(),
                )

    assert result.status == 'not_found'
    assert result.search_folder == resolved


def test_not_found_remake_uses_old_subfolder():
    resolved = r'C:\Workorders\GRUPO\Old'

    with patch('app.services.work_queue_service.resolve_work_search_path', return_value=resolved):
        with patch('app.services.work_queue_service.os.path.exists', return_value=True):
            with patch('app.services.work_queue_service.find_work_in_directory', return_value=None):
                result = search_work_for_queue(
                    'MISSING',
                    r'C:\Workorders',
                    'GRUPO',
                    is_remake=True,
                    skip_remake_screen=False,
                    queued_paths=[],
                    defined_paper_size=None,
                    defined_color=None,
                    db=_FakeDb(),
                )

    assert result.status == 'not_found'
    assert result.search_folder == resolved
