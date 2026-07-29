import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.decorators.auth_decorator import jwt_required, get_current_user
from app.decorators.role_decorator import require_profile, get_user_profile
from app.services.oferta_gestion_service import OfertaGestionService
from app.services.oferta_pausada_service import OfertaPausadaService
from app.services.oferta_especial_service import OfertaEspecialService
from app.repositories.user_repository import UserRepository
from app.dependencies import get_db_pg
from app.schemas.oferta_gestion_schema import (
    # Catálogos
    AccionConSubaccionesResponse,
    AccionCatalogoResponse,
    CreateAccionRequest,
    UpdateAccionRequest,
    SubaccionCatalogoResponse,
    CreateSubaccionRequest,
    UpdateSubaccionRequest,
    ConceptoCountResponse,
    # Gestión
    CongelarOfertaRequest,
    CongelarOfertaResponse,
    MiOfertaResponse,
    GestionarOfertaRequest,
    GestionarOfertaResponse,
    DescongelarOfertaRequest,
    DescongelarOfertaResponse,
    ReasignarOfertaRequest,
    ReasignarOfertaResponse,
    OfertasEnTramiteListResponse,
    # Configuración
    ConfiguracionResponse,
    UpdateConfiguracionRequest,
    # Configuración Global Avanzada
    ConfiguracionGlobalAvanzadaUpdate,
    ConfiguracionGlobalAvanzadaResponse,
    ConceptoDisponible,
    HistorialConfiguracionResponse,
    # Histórico
    HistoricoEstadoResponse,
    GestionDetalleResponse,
    ProductividadResponse,
    # Oferta Pausada
    PausarOfertaRequest,
    PausarOfertaResponse,
    ReanudarOfertaRequest,
    ReanudarOfertaResponse,
    OfertaPausadaListResponse,
    ConfiguracionPausadaResponse,
    UpdateConfiguracionPausadaRequest,
    LiberarOfertaPausadaRequest,
    LiberarOfertaPausadaResponse,
    # MALO y RFS - Solo liberación
    LiberarConceptoEspecialRequest,
    LiberarConceptoEspecialResponse,
    # Genéricos
    SuccessResponse,
    ErrorResponse
)
from app.schemas.oferta_especial_schema import (
    OfertasPausadasListResponse,
    OfertasMaloListResponse,
    OfertasRfsListResponse,
    OfertasEspecialesResumenResponse,
    OrderByEnum,
    OrderDirectionEnum
)
from app.services.oferta_pausada_service import OfertaPausadaService

router = APIRouter(prefix="/v1/ofertas", tags=["ofertas"])
logger = logging.getLogger("ofertas_routes")


# ==========================================
# UTILIDADES
# ==========================================

def get_user_data_from_request(request: Request, db: Session) -> dict:
    """Obtiene los datos del usuario desde el request"""
    payload = getattr(request.state, "payload", None)
    if not payload:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    user_id = payload.get("user_id")
    user_repository = UserRepository(db)
    user = user_repository.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener IP del cliente
    ip_address = request.client.host if request.client else None
    
    return {
        'login': user.login,
        'nombre': user.full_name,
        'profile_id': user.profile_id,
        'user_id': str(user.id),
        'ip_address': ip_address
    }


# ==========================================
# GRUPO 1: CATÁLOGOS (Acciones y Subacciones)
# ==========================================

@router.get(
    "/catalogo/acciones",
    response_model=list[AccionConSubaccionesResponse],
    dependencies=[Depends(jwt_required)],
    summary="Listar todas las acciones con sus subacciones"
)
async def get_acciones_catalogo(db: Session = Depends(get_db_pg)):
    """
    Obtiene todas las acciones del catálogo con sus subacciones asociadas.
    Disponible para todos los usuarios autenticados.
    """
    try:
        service = OfertaGestionService(db)
        acciones = service.get_all_acciones_con_subacciones()
        return acciones
    except Exception as e:
        logger.error(f"Error al obtener catálogo de acciones: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener catálogo de acciones"
        )


@router.post(
    "/catalogo/acciones",
    response_model=AccionCatalogoResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Crear nueva acción (SuperUser)"
)
async def create_accion(request: CreateAccionRequest, db: Session = Depends(get_db_pg)):
    """
    Crea una nueva acción en el catálogo.
    Solo disponible para SuperUser (profile_id = 1).
    """
    try:
        service = OfertaGestionService(db)
        accion = service.create_accion(
            nombre=request.nombre,
            descripcion=request.descripcion,
            orden=request.orden
        )
        
        if not accion:
            raise HTTPException(
                status_code=400,
                detail="No se pudo crear la acción. Puede que ya exista."
            )
        
        return accion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear acción: {e}")
        raise HTTPException(status_code=500, detail="Error al crear acción")


@router.put(
    "/catalogo/acciones/{accion_id}",
    response_model=AccionCatalogoResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Actualizar acción (SuperUser)"
)
async def update_accion(accion_id: str, request: UpdateAccionRequest, db: Session = Depends(get_db_pg)):
    """
    Actualiza una acción existente.
    Solo disponible para SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        accion = service.update_accion(accion_id, request.dict(exclude_none=True))
        
        if not accion:
            raise HTTPException(status_code=404, detail="Acción no encontrada")
        
        return accion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar acción: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar acción")


@router.delete(
    "/catalogo/acciones/{accion_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Eliminar acción (SuperUser)"
)
async def delete_accion(accion_id: str, db: Session = Depends(get_db_pg)):
    """
    Elimina (desactiva) una acción.
    Solo disponible para SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        success = service.delete_accion(accion_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Acción no encontrada")
        
        return SuccessResponse(
            message="Acción eliminada correctamente",
            data={"accion_id": accion_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar acción: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar acción")


@router.post(
    "/catalogo/subacciones",
    response_model=SubaccionCatalogoResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Crear nueva subacción (SuperUser)"
)
async def create_subaccion(request: CreateSubaccionRequest, db: Session = Depends(get_db_pg)):
    """
    Crea una nueva subacción asociada a una acción.
    Solo disponible para SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        subaccion = service.create_subaccion(
            accion_id=request.accion_id,
            nombre=request.nombre,
            orden=request.orden
        )
        
        if not subaccion:
            raise HTTPException(
                status_code=400,
                detail="No se pudo crear la subacción. Verifica que la acción exista."
            )
        
        return subaccion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear subacción: {e}")
        raise HTTPException(status_code=500, detail="Error al crear subacción")


@router.put(
    "/catalogo/subacciones/{subaccion_id}",
    response_model=SubaccionCatalogoResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Actualizar subacción (SuperUser)"
)
async def update_subaccion(subaccion_id: str, request: UpdateSubaccionRequest, db: Session = Depends(get_db_pg)):
    """
    Actualiza una subacción existente.
    Solo disponible para SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        subaccion = service.update_subaccion(subaccion_id, request.dict(exclude_none=True))
        
        if not subaccion:
            raise HTTPException(status_code=404, detail="Subacción no encontrada")
        
        return subaccion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar subacción: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar subacción")


@router.delete(
    "/catalogo/subacciones/{subaccion_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Eliminar subacción (SuperUser)"
)
async def delete_subaccion(subaccion_id: str, db: Session = Depends(get_db_pg)):
    """
    Elimina (desactiva) una subacción.
    Solo disponible para SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        success = service.delete_subaccion(subaccion_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Subacción no encontrada")
        
        return SuccessResponse(
            message="Subacción eliminada correctamente",
            data={"subaccion_id": subaccion_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar subacción: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar subacción")


# ==========================================
# GRUPO 2: CONCEPTOS DE OFERTAS
# ==========================================

@router.get(
    "/conceptos",
    response_model=list[ConceptoCountResponse],
    dependencies=[Depends(jwt_required)],
    summary="Obtener todos los conceptos con cantidad disponible"
)
async def get_conceptos_con_cantidad(db: Session = Depends(get_db_pg)):
    """
    Obtiene todos los conceptos únicos con la cantidad de ofertas disponibles en estado ABIERTO.
    
    - Excluye conceptos ANULA y ANULA-C
    - Solo cuenta ofertas en estado ABIERTO
    - Ordenados alfabéticamente por concepto
    
    Disponible para todos los usuarios autenticados.
    """
    try:
        service = OfertaGestionService(db)
        conceptos = service.get_conceptos_with_count()
        return conceptos
    except Exception as e:
        logger.error(f"Error al obtener conceptos con cantidad: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener conceptos con cantidad"
        )


# ==========================================
# GRUPO 3: GESTIÓN DE OFERTAS (Usuario Regular)
# ==========================================

@router.post(
    "/congelar",
    response_model=CongelarOfertaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([4]))],
    summary="Congelar/Tomar una oferta (Usuario Regular)"
)
async def congelar_oferta(request: Request, body: Optional[CongelarOfertaRequest] = None, db: Session = Depends(get_db_pg)):
    """
    Congela una oferta disponible asignándola al usuario autenticado.
    
    - Si se proporciona 'oferta': congela esa oferta específica (ignora 'concepto')
    - Si NO se proporciona 'oferta': busca según configuración global
    - Si se proporciona 'concepto' (sin 'oferta'): busca solo ofertas de ese concepto
    - Solo permite 1 oferta EN_TRAMITE por usuario
    - Solo disponible para usuarios Regular (profile_id = 4)
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(request, db)
        
        # Si se envía oferta específica, tiene prioridad (ignora concepto)
        oferta_numero = body.oferta if body else None
        concepto = body.concepto if body and not body.oferta else None
        
        resultado, error = service.congelar_oferta(usuario_data, oferta_numero, concepto)
        
        if error:
            if "ya tienes una oferta" in error.lower():
                raise HTTPException(status_code=409, detail=error)
            elif "no hay ofertas disponibles" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=400, detail=error)
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al congelar oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al congelar oferta")


@router.get(
    "/mi-oferta",
    response_model=MiOfertaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([4]))],
    summary="Consultar mi oferta actual (Usuario Regular)"
)
async def get_mi_oferta(request: Request, db: Session = Depends(get_db_pg)):
    """
    Obtiene la oferta actualmente asignada al usuario autenticado.
    Solo disponible para usuarios Regular.
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(request, db)
        oferta = service.get_mi_oferta(usuario_data['login'])
        
        if not oferta:
            raise HTTPException(
                status_code=404,
                detail="No tienes ofertas en trámite"
            )
        
        return oferta
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener mi oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener oferta")


@router.post(
    "/gestionar",
    response_model=GestionarOfertaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([4]))],
    summary="Gestionar/Cerrar oferta (Usuario Regular)"
)
async def gestionar_oferta(request: Request, body: GestionarOfertaRequest, db: Session = Depends(get_db_pg)):
    """
    Gestiona y cierra una oferta con acción, subacción y observación.
    
    **Detección automática de conceptos especiales:**
    - Si la acción es "MALO": aplica lógica especial, guarda concepto anterior
    - Si la acción es "RFS": aplica lógica especial, guarda concepto anterior
    - Otras acciones: gestión normal
    
    **Efecto:**
    - Cambia el estado de la oferta a CERRADO
    - Registra el detalle de gestión
    - Libera al usuario para tomar otra oferta
    
    Solo disponible para usuarios Regular (profile_id = 4).
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(request, db)
        
        resultado, error = service.gestionar_oferta(
            oferta_numero=body.oferta,
            accion_id=body.accion_id,
            subaccion_id=body.subaccion_id,
            observacion=body.observacion,
            usuario_data=usuario_data
        )
        
        if error:
            if "no está asignada" in error.lower():
                raise HTTPException(status_code=403, detail=error)
            elif "no encontrada" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=400, detail=error)
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al gestionar oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al gestionar oferta")


# ==========================================
# GRUPO 4: SUPERVISIÓN (Supervisor/SuperUser)
# ==========================================

@router.post(
    "/descongelar",
    response_model=DescongelarOfertaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Descongelar oferta (Supervisor/SuperUser)"
)
async def descongelar_oferta(request: Request, body: DescongelarOfertaRequest, db: Session = Depends(get_db_pg)):
    """
    Descongela una oferta liberándola de su asignación actual.
    
    - Cambia el estado a ABIERTO
    - Limpia datos de asignación
    - Solo disponible para Supervisor y SuperUser
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(request, db)
        
        resultado, error = service.descongelar_oferta(
            oferta_numero=body.oferta,
            motivo=body.motivo,
            supervisor_data=usuario_data
        )
        
        if error:
            if "no encontrada" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=400, detail=error)
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al descongelar oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al descongelar oferta")


@router.post(
    "/reasignar",
    response_model=ReasignarOfertaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Reasignar oferta (Supervisor/SuperUser)"
)
async def reasignar_oferta(request: Request, body: ReasignarOfertaRequest, db: Session = Depends(get_db_pg)):
    """
    Reasigna una oferta a otro asesor específico.
    
    - Valida que el asesor destino no tenga otra oferta
    - Solo puede reasignar a usuarios Regular
    - Solo disponible para Supervisor y SuperUser
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(request, db)
        
        resultado, error = service.reasignar_oferta(
            oferta_numero=body.oferta,
            asesor_login=body.asesor_login,
            motivo=body.motivo,
            supervisor_data=usuario_data
        )
        
        if error:
            if "ya tiene una oferta" in error.lower():
                raise HTTPException(status_code=409, detail=error)
            elif "no encontrado" in error.lower():
                raise HTTPException(status_code=404, detail=error)
            else:
                raise HTTPException(status_code=400, detail=error)
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al reasignar oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al reasignar oferta")


@router.get(
    "/en-tramite",
    response_model=OfertasEnTramiteListResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Listar ofertas en trámite (Supervisor/SuperUser)"
)
async def get_ofertas_en_tramite(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(50, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene todas las ofertas en estado EN_TRAMITE.
    Dashboard para supervisores.
    Solo disponible para Supervisor y SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        resultado = service.get_ofertas_en_tramite(page=page, limit=limit)
        return resultado
    except Exception as e:
        logger.error(f"Error al obtener ofertas en trámite: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener ofertas en trámite"
        )


# ==========================================
# GRUPO 5: CONFIGURACIÓN
# ==========================================

# ==========================================
# CONFIGURACIÓN GLOBAL AVANZADA
# (Rutas específicas deben ir ANTES de rutas con parámetros dinámicos)
# ==========================================

@router.get(
    "/configuracion/avanzada",
    response_model=ConfiguracionGlobalAvanzadaResponse,
    dependencies=[Depends(jwt_required)],
    summary="Obtener configuración GLOBAL activa"
)
async def get_configuracion_global(
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene la configuración GLOBAL activa que aplica a todos los usuarios.
    Cualquier usuario autenticado puede consultar.
    """
    try:
        service = OfertaGestionService(db)
        config = service.get_configuracion_global_avanzada()
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener configuración global: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener configuración")


@router.put(
    "/configuracion/avanzada",
    response_model=ConfiguracionGlobalAvanzadaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Actualizar configuración GLOBAL (Solo Superuser/Supervisor)"
)
async def update_configuracion_global(
    config_data: ConfiguracionGlobalAvanzadaUpdate,
    request: Request,
    db: Session = Depends(get_db_pg)
):
    """
    Actualiza la configuración GLOBAL que afecta a TODOS los usuarios.
    
    Solo Superuser (profile_id=1) y Supervisor (profile_id=2) pueden modificar.
    
    Parámetros configurables:
    - Campo de ordenamiento: created_at (Fecha Ingreso Gestor) o fecha_creado (Fecha Creado CRM)
    - Dirección de orden: ASC o DESC
    - Filtro de conceptos: TODOS o ESPECIFICOS
    - Filtro de tipo trabajo: TODOS, NUEVO o CAMBIO
    - Filtro de regional: TODOS o ESPECIFICAS
    """
    try:
        usuario_data = get_user_data_from_request(request, db)
        service = OfertaGestionService(db)
        
        config = service.update_configuracion_global_avanzada(
            config_data=config_data.dict(),
            updated_by=usuario_data['login'],
            ip_address=usuario_data.get('ip_address')
        )
        
        if not config:
            raise HTTPException(status_code=400, detail="Error al actualizar configuración")
        
        logger.info(f"✅ Configuración global actualizada por {usuario_data['login']}")
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar configuración global: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")


@router.get(
    "/configuracion/avanzada/historial",
    response_model=list[HistorialConfiguracionResponse],
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Obtener historial de cambios de configuración GLOBAL"
)
async def get_historial_configuracion_global(
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene el historial completo de cambios de configuración GLOBAL.
    Solo Superuser y Supervisor pueden consultar.
    """
    try:
        service = OfertaGestionService(db)
        return service.get_historial_configuracion_global()
        
    except Exception as e:
        logger.error(f"Error al obtener historial: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener historial")


@router.get(
    "/configuracion/conceptos-sistema",
    response_model=list[ConceptoDisponible],
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Listar TODOS los conceptos del sistema (Para configuración)"
)
async def get_conceptos_sistema(
    db: Session = Depends(get_db_pg)
):
    """
    Lista TODOS los conceptos disponibles en el sistema.
    Usado para configurar cuáles conceptos permitir.
    
    Solo Superuser y Supervisor pueden consultar.
    """
    try:
        service = OfertaGestionService(db)
        return service.get_conceptos_disponibles_sistema()
        
    except Exception as e:
        logger.error(f"Error al obtener conceptos sistema: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener conceptos")


@router.get(
    "/configuracion/conceptos-disponibles",
    response_model=list[ConceptoDisponible],
    dependencies=[Depends(jwt_required)],
    summary="Listar conceptos disponibles según configuración GLOBAL (Para congelar)"
)
async def get_conceptos_disponibles(
    db: Session = Depends(get_db_pg)
):
    """
    Lista conceptos disponibles para el usuario según configuración GLOBAL.
    
    Si configuración = TODOS: retorna todos los conceptos
    Si configuración = ESPECIFICOS: retorna solo los conceptos permitidos
    
    Cualquier usuario autenticado puede consultar para ver qué puede congelar.
    """
    try:
        service = OfertaGestionService(db)
        return service.get_conceptos_disponibles_usuario()
        
    except Exception as e:
        logger.error(f"Error al obtener conceptos disponibles: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener conceptos")


@router.get(
    "/configuracion/regionales-disponibles",
    response_model=list[str],
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Listar regionales disponibles (Para configuración)"
)
async def get_regionales_disponibles(
    db: Session = Depends(get_db_pg)
):
    """
    Lista todas las regionales únicas disponibles en ofertas ABIERTAS.
    NULL se muestra como 'DEFAULT'.
    
    Solo Superuser y Supervisor pueden consultar.
    """
    try:
        service = OfertaGestionService(db)
        return service.get_regionales_disponibles()
        
    except Exception as e:
        logger.error(f"Error al obtener regionales: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener regionales")


# ==========================================
# CONFIGURACIÓN POR PERFIL (LEGACY)
# ==========================================

@router.get(
    "/configuracion/{profile_id}",
    response_model=ConfiguracionResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Obtener configuración de orden (SuperUser)"
)
async def get_configuracion(profile_id: int, db: Session = Depends(get_db_pg)):
    """
    Obtiene la configuración de orden de búsqueda para un perfil.
    Solo disponible para SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        config = service.get_configuracion(profile_id)
        
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"No hay configuración para profile_id {profile_id}"
            )
        
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener configuración: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener configuración")


@router.put(
    "/configuracion",
    response_model=ConfiguracionResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1]))],
    summary="Actualizar configuración de orden (SuperUser)"
)
async def update_configuracion(request: Request, body: UpdateConfiguracionRequest, db: Session = Depends(get_db_pg)):
    """
    Actualiza o crea la configuración de orden de búsqueda para un perfil.
    
    - orden_busqueda: ASC (más antigua) o DESC (más reciente)
    - Solo disponible para SuperUser
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(request, db)
        
        config = service.update_configuracion(
            profile_id=body.profile_id,
            orden_busqueda=body.orden_busqueda,
            descripcion=body.descripcion,
            updated_by=usuario_data['login']
        )
        
        if not config:
            raise HTTPException(
                status_code=400,
                detail="No se pudo actualizar la configuración"
            )
        
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar configuración: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")


# ==========================================
# GRUPO 6: HISTÓRICO Y REPORTES
# ==========================================

@router.get(
    "/historico/{oferta}",
    response_model=list[HistoricoEstadoResponse],
    dependencies=[Depends(jwt_required)],
    summary="Obtener histórico de estados de una oferta"
)
async def get_historico_oferta(oferta: str, db: Session = Depends(get_db_pg)):
    """
    Obtiene el histórico completo de cambios de estado de una oferta.
    Disponible para todos los usuarios autenticados.
    """
    try:
        service = OfertaGestionService(db)
        historico = service.get_historico_oferta(oferta)
        return historico
    except Exception as e:
        logger.error(f"Error al obtener histórico: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener histórico")


@router.get(
    "/gestion-detalle/{oferta}",
    response_model=GestionDetalleResponse,
    dependencies=[Depends(jwt_required)],
    summary="Obtener detalle de gestión de una oferta"
)
async def get_gestion_detalle(oferta: str, db: Session = Depends(get_db_pg)):
    """
    Obtiene el detalle de gestión (acción, subacción, observación) de una oferta cerrada.
    Disponible para todos los usuarios autenticados.
    """
    try:
        service = OfertaGestionService(db)
        detalle = service.get_gestion_detalle(oferta)
        
        if not detalle:
            raise HTTPException(
                status_code=404,
                detail="No se encontró detalle de gestión para esta oferta"
            )
        
        return detalle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener detalle de gestión: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener detalle")


@router.get(
    "/reportes/productividad",
    response_model=ProductividadResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Reporte de productividad (Supervisor/SuperUser)"
)
async def get_reporte_productividad(
    usuario: str = Query(..., description="Login del usuario"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde (ISO 8601)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta (ISO 8601)"),
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene reporte de productividad de un usuario.
    
    - Total de ofertas gestionadas
    - Distribución por acción
    - Tiempo promedio de gestión
    
    Solo disponible para Supervisor y SuperUser.
    """
    try:
        service = OfertaGestionService(db)
        reporte = service.get_productividad_usuario(
            usuario_login=usuario,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        if 'error' in reporte:
            raise HTTPException(status_code=404, detail=reporte['error'])
        
        return reporte
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener reporte de productividad: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener reporte"
        )


# ==========================================
# GRUPO: OFERTA PAUSADA
# ==========================================

@router.post(
    "/pausar",
    response_model=PausarOfertaResponse,
    dependencies=[Depends(jwt_required)],
    summary="Pausar oferta actual (Asesor)"
)
async def pausar_oferta(request: PausarOfertaRequest, http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Pausa temporalmente la oferta que está gestionando el asesor.
    
    **Validaciones:**
    - La oferta debe estar EN_TRAMITE
    - Debe haber transcurrido el tiempo mínimo (configurable, default 7 min)
    - El asesor no debe exceder el máximo de ofertas pausadas (configurable, default 3)
    
    **Efecto:**
    - Concepto cambia a "OFERTA PAUSADA"
    - Estado cambia a "EN_TRAMITE_PAUSADO"
    - Se registra en tracking de pausas
    
    Solo disponible para asesores (profile_id = 3).
    """
    try:
        pausada_service = OfertaPausadaService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        resultado, error = pausada_service.pausar_oferta(
            oferta_numero=request.oferta,
            usuario_data=usuario_data
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al pausar oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al pausar oferta")


@router.post(
    "/reanudar",
    response_model=ReanudarOfertaResponse,
    dependencies=[Depends(jwt_required)],
    summary="Reanudar oferta pausada (Asesor)"
)
async def reanudar_oferta(request: ReanudarOfertaRequest, http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Reanuda una oferta que el asesor había pausado.
    
    **Efecto:**
    - Concepto vuelve al que tenía antes de pausar
    - Estado cambia a "EN_TRAMITE"
    - Se actualiza el tracking de pausa
    
    Solo disponible para asesores (profile_id = 3).
    """
    try:
        pausada_service = OfertaPausadaService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        resultado, error = pausada_service.reanudar_oferta(
            oferta_numero=request.oferta,
            usuario_data=usuario_data
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al reanudar oferta: {e}")
        raise HTTPException(status_code=500, detail="Error al reanudar oferta")


@router.get(
    "/mis-pausadas",
    response_model=OfertaPausadaListResponse,
    dependencies=[Depends(jwt_required)],
    summary="Listar mis ofertas pausadas (Asesor)"
)
async def get_mis_ofertas_pausadas(http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Obtiene la lista de ofertas que el asesor tiene actualmente pausadas.
    
    Retorna información sobre:
    - Número de oferta
    - Concepto anterior (antes de pausar)
    - Fecha de pausa
    - Tiempo transcurrido en minutos
    
    Solo disponible para asesores (profile_id = 3).
    """
    try:
        pausada_service = OfertaPausadaService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        ofertas = pausada_service.get_mis_ofertas_pausadas(usuario_data['login'])
        
        return {
            'ofertas': ofertas,
            'total': len(ofertas)
        }
        
    except Exception as e:
        logger.error(f"Error al obtener ofertas pausadas: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener ofertas pausadas")


@router.get(
    "/config-pausada",
    response_model=ConfiguracionPausadaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Obtener configuración de pausas (Supervisor/SuperUser)"
)
async def get_config_pausada(db: Session = Depends(get_db_pg)):
    """
    Obtiene la configuración actual de ofertas pausadas.
    
    Retorna:
    - Tiempo mínimo en minutos antes de poder pausar
    - Cantidad máxima de ofertas pausadas por asesor
    
    Solo disponible para Supervisor y SuperUser (profile_id = 1, 2).
    """
    try:
        pausada_service = OfertaPausadaService(db)
        config = pausada_service.get_configuracion()
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener configuración pausada: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener configuración")


@router.put(
    "/config-pausada",
    response_model=ConfiguracionPausadaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Actualizar configuración de pausas (Supervisor/SuperUser)"
)
async def update_config_pausada(request: UpdateConfiguracionPausadaRequest, http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Actualiza la configuración de ofertas pausadas.
    
    Permite modificar:
    - `tiempo_minimo_pausa_minutos`: Tiempo mínimo antes de pausar (>= 0)
    - `max_ofertas_pausadas_por_asesor`: Cantidad máxima de ofertas pausadas (>= 1)
    
    Solo disponible para Supervisor y SuperUser (profile_id = 1, 2).
    """
    try:
        pausada_service = OfertaPausadaService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        resultado, error = pausada_service.actualizar_configuracion(
            tiempo_minimo=request.tiempo_minimo_pausa_minutos,
            max_ofertas=request.max_ofertas_pausadas_por_asesor,
            updated_by=usuario_data['login']
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar configuración pausada: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar configuración")


@router.post(
    "/liberar-pausada",
    response_model=LiberarOfertaPausadaResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Liberar oferta pausada (Supervisor/SuperUser)"
)
async def liberar_oferta_pausada(request: LiberarOfertaPausadaRequest, http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Libera una oferta que está pausada por un asesor.
    
    **Efecto:**
    - Concepto vuelve al que tenía antes de pausar
    - Estado cambia a "ABIERTO"
    - Se desasigna del asesor
    - Se actualiza el tracking de pausa
    
    Solo disponible para Supervisor y SuperUser (profile_id = 1, 2).
    """
    try:
        pausada_service = OfertaPausadaService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        resultado, error = pausada_service.liberar_oferta_pausada(
            oferta_numero=request.oferta,
            supervisor_data=usuario_data,
            motivo=request.motivo
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al liberar oferta pausada: {e}")
        raise HTTPException(status_code=500, detail="Error al liberar oferta pausada")


# ==========================================
# GRUPO: CONCEPTOS ESPECIALES (MALO y RFS) - LIBERACIÓN
# ==========================================

@router.post(
    "/liberar-malo",
    response_model=LiberarConceptoEspecialResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Liberar oferta MALO (Supervisor/SuperUser)"
)
async def liberar_malo(request: LiberarConceptoEspecialRequest, http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Libera una oferta que está en concepto MALO.
    
    **Efecto:**
    - Concepto vuelve al que tenía antes de MALO
    - Estado cambia a "ABIERTO"
    - La oferta vuelve a estar disponible
    
    Solo disponible para Supervisor y SuperUser (profile_id = 1, 2).
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        resultado, error = service.liberar_oferta_malo(
            oferta_numero=request.oferta,
            supervisor_data=usuario_data,
            motivo=request.motivo
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al liberar oferta MALO: {e}")
        raise HTTPException(status_code=500, detail="Error al liberar oferta MALO")


@router.post(
    "/liberar-rfs",
    response_model=LiberarConceptoEspecialResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Liberar oferta RFS (Supervisor/SuperUser)"
)
async def liberar_rfs(request: LiberarConceptoEspecialRequest, http_request: Request, db: Session = Depends(get_db_pg)):
    """
    Libera una oferta que está en concepto RFS.
    
    **Efecto:**
    - Concepto vuelve al que tenía antes de RFS
    - Estado cambia a "ABIERTO"
    - La oferta vuelve a estar disponible
    
    Solo disponible para Supervisor y SuperUser (profile_id = 1, 2).
    """
    try:
        service = OfertaGestionService(db)
        usuario_data = get_user_data_from_request(http_request, db)
        
        resultado, error = service.liberar_oferta_rfs(
            oferta_numero=request.oferta,
            supervisor_data=usuario_data,
            motivo=request.motivo
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al liberar oferta RFS: {e}")
        raise HTTPException(status_code=500, detail="Error al liberar oferta RFS")


# ==========================================
# LISTADO DE OFERTAS ESPECIALES
# ==========================================

@router.get(
    "/pausadas/listar",
    response_model=OfertasPausadasListResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Listar ofertas pausadas",
    description="Lista todas las ofertas pausadas actualmente (solo supervisores y superusers)"
)
async def listar_ofertas_pausadas(
    uen: Optional[str] = Query(None, description="Filtro por UEN (RESIDENCIAL/EMPRESARIAL/ALL)"),
    usuario_login: Optional[str] = Query(None, description="Filtro por login del asesor"),
    fecha_desde: Optional[datetime] = Query(None, description="Filtro fecha desde (YYYY-MM-DD HH:MM:SS)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Filtro fecha hasta (YYYY-MM-DD HH:MM:SS)"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad de registros (máx 500)"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    order_by: OrderByEnum = Query(OrderByEnum.FECHA_PAUSA, description="Campo de ordenamiento"),
    order_direction: OrderDirectionEnum = Query(OrderDirectionEnum.DESC, description="Dirección de ordenamiento"),
    db: Session = Depends(get_db_pg)
):
    """
    Lista todas las ofertas con estado EN_TRAMITE_PAUSADO.
    
    - **Permisos**: Supervisor (3), SuperUsuario (1)
    - **Filtros**: UEN, usuario, rango de fechas
    - **Paginación**: limit y offset
    - **Ordenamiento**: Por fecha_pausa u oferta
    - **Retorna**: Lista de ofertas pausadas con datos del asesor, tiempo pausada y campos de la oferta
    """
    try:
        service = OfertaEspecialService(db)
        
        resultado = service.listar_ofertas_pausadas(
            uen=uen,
            usuario_login=usuario_login,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit,
            offset=offset,
            order_by=order_by.value,
            order_direction=order_direction.value
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar ofertas pausadas: {e}")
        raise HTTPException(status_code=500, detail="Error al listar ofertas pausadas")


@router.get(
    "/malo/listar",
    response_model=OfertasMaloListResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Listar ofertas MALO",
    description="Lista todas las ofertas marcadas como MALO (solo supervisores y superusers)"
)
async def listar_ofertas_malo(
    uen: Optional[str] = Query(None, description="Filtro por UEN (RESIDENCIAL/EMPRESARIAL/ALL)"),
    usuario_login: Optional[str] = Query(None, description="Filtro por login del asesor que marcó"),
    fecha_desde: Optional[datetime] = Query(None, description="Filtro fecha desde (YYYY-MM-DD HH:MM:SS)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Filtro fecha hasta (YYYY-MM-DD HH:MM:SS)"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad de registros (máx 500)"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    order_by: OrderByEnum = Query(OrderByEnum.FECHA_GESTION, description="Campo de ordenamiento"),
    order_direction: OrderDirectionEnum = Query(OrderDirectionEnum.DESC, description="Dirección de ordenamiento"),
    db: Session = Depends(get_db_pg)
):
    """
    Lista todas las ofertas con concepto MALO (datos incorrectos).
    
    - **Permisos**: Supervisor (3), SuperUsuario (1)
    - **Filtros**: UEN, usuario, rango de fechas
    - **Paginación**: limit y offset
    - **Ordenamiento**: Por fecha_gestion u oferta
    - **Retorna**: Lista de ofertas MALO con datos del asesor, gestión y campos de la oferta
    """
    try:
        service = OfertaEspecialService(db)
        
        resultado = service.listar_ofertas_malo(
            uen=uen,
            usuario_login=usuario_login,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit,
            offset=offset,
            order_by=order_by.value,
            order_direction=order_direction.value
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar ofertas MALO: {e}")
        raise HTTPException(status_code=500, detail="Error al listar ofertas MALO")


@router.get(
    "/rfs/listar",
    response_model=OfertasRfsListResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Listar ofertas RFS",
    description="Lista todas las ofertas marcadas como RFS - Ready For Service (solo supervisores y superusers)"
)
async def listar_ofertas_rfs(
    uen: Optional[str] = Query(None, description="Filtro por UEN (RESIDENCIAL/EMPRESARIAL/ALL)"),
    usuario_login: Optional[str] = Query(None, description="Filtro por login del asesor que marcó"),
    fecha_desde: Optional[datetime] = Query(None, description="Filtro fecha desde (YYYY-MM-DD HH:MM:SS)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Filtro fecha hasta (YYYY-MM-DD HH:MM:SS)"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad de registros (máx 500)"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    order_by: OrderByEnum = Query(OrderByEnum.FECHA_GESTION, description="Campo de ordenamiento"),
    order_direction: OrderDirectionEnum = Query(OrderDirectionEnum.DESC, description="Dirección de ordenamiento"),
    db: Session = Depends(get_db_pg)
):
    """
    Lista todas las ofertas con concepto RFS (Ready For Service).
    
    - **Permisos**: Supervisor (3), SuperUsuario (1)
    - **Filtros**: UEN, usuario, rango de fechas
    - **Paginación**: limit y offset
    - **Ordenamiento**: Por fecha_gestion u oferta
    - **Retorna**: Lista de ofertas RFS con datos del asesor, gestión y campos de la oferta
    """
    try:
        service = OfertaEspecialService(db)
        
        resultado = service.listar_ofertas_rfs(
            uen=uen,
            usuario_login=usuario_login,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit,
            offset=offset,
            order_by=order_by.value,
            order_direction=order_direction.value
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar ofertas RFS: {e}")
        raise HTTPException(status_code=500, detail="Error al listar ofertas RFS")


@router.get(
    "/especiales/resumen",
    response_model=OfertasEspecialesResumenResponse,
    dependencies=[Depends(jwt_required), Depends(require_profile([1, 3]))],
    summary="Resumen de ofertas especiales",
    description="Obtiene resumen consolidado de todas las ofertas especiales (solo supervisores y superusers)"
)
async def get_resumen_ofertas_especiales(
    db: Session = Depends(get_db_pg)
):
    """
    Obtiene un resumen consolidado de ofertas especiales para dashboard.
    
    - **Permisos**: Supervisor (3), SuperUsuario (1)
    - **Retorna**: Contadores de ofertas pausadas, MALO, RFS y total general
    - **Uso**: Ideal para dashboards y vistas de supervisión
    """
    try:
        service = OfertaEspecialService(db)
        
        resultado = service.get_resumen_dashboard()
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error al obtener resumen ofertas especiales: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener resumen")


# ==========================================
# HEALTH CHECK
# ==========================================

@router.get(
    "/health",
    summary="Health check del módulo de ofertas"
)
async def health_check(db: Session = Depends(get_db_pg)):
    """
    Verifica el estado del módulo de gestión de ofertas.
    """
    return {
        "status": "healthy",
        "module": "ofertas_gestion",
        "timestamp": datetime.now().isoformat()
    }

