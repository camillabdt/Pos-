from percurso.dominio.metricas import h5_index, h_index, i10_index


def test_indices():
    assert h_index([10, 8, 5, 4, 3]) == 4
    assert h_index([]) == 0 and h_index([0, None]) == 0
    assert i10_index([10, 9, 25, None]) == 2
    assert h5_index([(2026, 5), (2025, 5), (2020, 100)], 2026) == 2
