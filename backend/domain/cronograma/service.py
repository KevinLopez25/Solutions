"""
Servicio de dominio: generación del cronograma XLSX.
"""
import base64

from domain.cronograma.entities import (
    GenerarCronogramaRequest, GenerarCronogramaResponse,
)
from infrastructure.generators import cronograma_excel


def generar_cronograma(request: GenerarCronogramaRequest) -> GenerarCronogramaResponse:
    config = request.model_dump()
    result_bytes = cronograma_excel.generate_cronograma(config)

    filename = f"Cronograma_{request.proyecto or 'Proyecto'}.xlsx"
    return GenerarCronogramaResponse(
        filename=filename,
        content_b64=base64.b64encode(result_bytes).decode(),
    )
