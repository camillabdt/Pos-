"""Implementação Firestore. Requer `firebase-admin` e credenciais
(GOOGLE_APPLICATION_CREDENTIALS apontando para um JSON FORA do repositório,
ou Application Default Credentials no Cloud Run)."""

from __future__ import annotations

from percurso.store.base import Doc


class FirestoreStore:
    def __init__(self, project_id: str | None = None) -> None:
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            opts = {"projectId": project_id} if project_id else None
            firebase_admin.initialize_app(options=opts)
        self._db = firestore.client()

    def get(self, colecao: str, id: str) -> Doc | None:
        snap = self._db.collection(colecao).document(id).get()
        return {**snap.to_dict(), "id": snap.id} if snap.exists else None

    def listar(self, colecao: str) -> list[Doc]:
        return [{**s.to_dict(), "id": s.id} for s in self._db.collection(colecao).stream()]

    def salvar(self, colecao: str, id: str, dados: Doc) -> None:
        self._db.collection(colecao).document(id).set({k: v for k, v in dados.items() if k != "id"})

    def apagar(self, colecao: str, id: str) -> bool:
        ref = self._db.collection(colecao).document(id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    def novo_id(self, colecao: str) -> str:
        return self._db.collection(colecao).document().id
