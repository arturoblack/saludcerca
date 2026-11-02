"""Guardar y leer historias clínicas cifrando el contenido sensible."""
from __future__ import annotations

from .cifrado import Cifrador
from .models import CAMPOS_CIFRADOS, NotaAlmacenada, NotaClinica
from .repository import Repository


def _contexto(paciente_id: str, nota_id: str) -> str:
    return f"{paciente_id}:{nota_id}"


def guardar_nota(repo: Repository, cif: Cifrador, nota: NotaClinica) -> NotaAlmacenada:
    datos = nota.model_dump(mode="json")
    sensible = {k: datos[k] for k in CAMPOS_CIFRADOS}
    almacenada = NotaAlmacenada(
        id=nota.id, paciente_id=nota.paciente_id, medico_id=nota.medico_id, cita_id=nota.cita_id,
        fecha=nota.fecha, adjuntos=nota.adjuntos, contenido=cif.cifrar(sensible, _contexto(nota.paciente_id, nota.id)),
    )
    return repo.add_nota(almacenada)


def leer_notas(repo: Repository, cif: Cifrador, paciente_id: str) -> list[NotaClinica]:
    notas = []
    for a in repo.list_notas(paciente_id):
        sensible = cif.descifrar(a.contenido, _contexto(a.paciente_id, a.id))
        notas.append(NotaClinica(id=a.id, paciente_id=a.paciente_id, medico_id=a.medico_id, cita_id=a.cita_id,
                                 fecha=a.fecha, adjuntos=a.adjuntos, **sensible))
    return notas
