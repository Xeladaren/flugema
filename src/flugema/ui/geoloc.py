import asyncio
import datetime
from typing import Any, Callable, Dict, List, Optional

from nicegui.element import Element
from nicegui.events import GenericEventArguments, handle_event

from ..utils.geo import GeoPos

class GeolocError(RuntimeError):
    """Erreur renvoyée par l'API de géolocalisation du navigateur."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f'[{code}] {message}')
        self.code = code
        self.message = message


class Geoloc(Element, component='geoloc.js'):

    def __init__(self, *,
                 watch: bool = False,
                 high_accuracy: bool = True,
                 timeout: float = 10.0,
                 maximum_age: float = 0.0,
                 on_position: Optional[Callable[..., Any]] = None,
                 on_error: Optional[Callable[..., Any]] = None) -> None:
        """Élément invisible donnant accès au GPS du navigateur.

        :param watch: démarre automatiquement un suivi continu (watchPosition)
        :param high_accuracy: demande la meilleure précision possible (GPS mobile)
        :param timeout: délai max, en secondes, accordé au navigateur
        :param maximum_age: âge max, en secondes, d'une position en cache
        :param on_position: callback appelé à chaque nouvelle position
        :param on_error: callback appelé en cas d'erreur / refus de permission
        """
        super().__init__()
        self._props['watch'] = watch
        self._props['high_accuracy'] = high_accuracy
        self._props['timeout'] = int(timeout * 1000)
        self._props['maximum_age'] = int(maximum_age * 1000)

        self.position: Optional[Dict[str, Any]] = None
        self._pending: List[asyncio.Future] = []
        self._on_position = on_position
        self._on_error = on_error

        self.on('position', self._handle_position)
        self.on('error', self._handle_error)

    def _handle_position(self, e: GenericEventArguments) -> None:
        self.position = e.args
        for future in self._pending:
            if not future.done():
                future.set_result(e.args)
        self._pending.clear()
        if self._on_position:
            handle_event(self._on_position, e)

    def _handle_error(self, e: GenericEventArguments) -> None:
        error = GeolocError(e.args.get('code', -1), e.args.get('message', 'unknown'))
        for future in self._pending:
            if not future.done():
                future.set_exception(error)
        self._pending.clear()
        if self._on_error:
            handle_event(self._on_error, e)
        elif not self._on_position:
            raise error  # aucun handler défini : on ne masque pas l'erreur

    def request(self) -> None:
        """Demande une position de façon *fire-and-forget* (résultat via `on_position`)."""
        self.run_method('request')

    async def get_position(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Demande une position et attend la réponse du navigateur.

        Lève `GeolocError` en cas de refus/échec, `asyncio.TimeoutError` si le
        navigateur ne répond pas à temps.
        """
        if timeout is None:
            timeout = self._props['timeout'] / 1000 + 5.0
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending.append(future)
        self.run_method('request')
        try:
            raw_value = await asyncio.wait_for(future, timeout)
            position = GeoPos(
                latitude=raw_value["latitude"],
                longitude=raw_value["longitude"],
                altitude=raw_value["altitude"],
                accuracy=raw_value["accuracy"],
                date=datetime.datetime.fromtimestamp(raw_value["timestamp"] / 1000.0, tz=datetime.UTC)
            )
            return position
        finally:
            if future in self._pending:
                self._pending.remove(future)

    def start_watch(self) -> None:
        """Démarre le suivi continu de la position."""
        self.run_method('start')

    def stop_watch(self) -> None:
        """Arrête le suivi continu de la position."""
        self.run_method('stop')

    def _handle_delete(self) -> None:
        for future in self._pending:
            if not future.done():
                future.cancel()
        self._pending.clear()
        super()._handle_delete()