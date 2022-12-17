from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any, List

import numpy as np
import numpy.typing as npt
import pandas as pd
from jax import random

from ananke.models.event import Events, EventRecords, SourceRecords
from ananke.models.geometry import Vectors3D
from ananke.models.detector import Detector
from ananke.schemas.event import SourceType
from .constants import defaults
from .event_generation import generate_muon_energy_losses
from .lightyield import (
    make_realistic_cascade_source,
)
from .photon_propagation.interface import AbstractPhotonPropagator
from .utils import proposal_setup


class AbstractPropagator(ABC):
    def __init__(
            self,
            detector: Detector,
            photon_propagator: AbstractPhotonPropagator,
            name: str,
            seed: int = defaults['seed'],
            **kwargs
    ) -> None:
        super().__init__()
        self.name = name
        self.detector = detector
        self.photon_propagator = photon_propagator
        self.seed = seed

    @abstractmethod
    def _convert(self, event_records: EventRecords, k1: Any) -> SourceRecords:
        pass

    def _convert_sources_to_source_records(
            self,
            event_id: int,
            sources_information: Tuple[
                npt.ArrayLike,
                npt.ArrayLike,
                npt.ArrayLike,
                npt.ArrayLike,
            ]
    ) -> SourceRecords:
        source_locations = sources_information[0]
        source_orientations = sources_information[1]
        source_times = sources_information[2]
        source_number_of_photons = sources_information[3]

        # early mask sources that are out of reach

        module_locations = np.array(self.detector.module_locations)

        dist_matrix = np.linalg.norm(
            source_locations[:, np.newaxis, ...]
            - module_locations[np.newaxis, ...],
            axis=-1,
        )

        # only consider photon sources within a certain distance to the module
        mask = np.any(dist_matrix < 300, axis=1)
        source_locations = Vectors3D.from_numpy(source_locations[mask])
        source_orientations = Vectors3D.from_numpy(source_orientations[mask])
        source_times = source_times[mask]
        source_number_of_photons = source_number_of_photons[mask]

        source_record_df = pd.concat(
            [
                source_locations.get_df_with_prefix('location_'),
                source_orientations.get_df_with_prefix('orientation_'),
            ], axis=1
        )

        source_record_df['event_id'] = event_id
        source_record_df['time'] = source_times
        source_record_df['number_of_photons'] = source_number_of_photons
        source_record_df['type'] = SourceType.STANDARD_CHERENKOV.value

        return SourceRecords(df=source_record_df)

    def propagate(self, events: EventRecords) -> Events:
        key, k1, k2 = random.split(random.PRNGKey(self.seed), 3)

        sources = self._convert(event_records=events, k1=k1)
        # TODO: Count In angular resolution
        hits = self.photon_propagator.propagate(events=events, sources=sources)
        event = Events(
            detector=self.detector,
            events=events,
            sources=sources,
            hits=hits
        )

        return event


class TrackPropagator(AbstractPropagator):
    def __init__(
            self,
            detector: Detector,
            photon_propagator: AbstractPhotonPropagator,
            name: str = "track",
            seed: int = defaults['seed'],
            **kwargs
    ) -> None:
        super().__init__(detector, photon_propagator, name, seed, **kwargs)
        self.proposal_propagator = proposal_setup()

    def _convert(self, event_records: EventRecords, k1: str) -> SourceRecords:
        source_records: List[SourceRecords] = []
        for index, event_record in event_records.df.iterrows():
            sources = generate_muon_energy_losses(
                self.proposal_propagator,
                event_record['energy'],
                event_record['length'],
                np.array(event_record['location']),
                np.array(event_record['orientation']),
                event_record['time'],
                k1,
                return_angle_distribution=True
            )

            event_source_records = self._convert_sources_to_source_records(
                event_record['event_id'],
                sources[:-1]
            )
            event_records.df.loc[index, 'length'] = sources[-1]
            source_records.append(event_source_records)

        return SourceRecords.concat(source_records)


class CascadePropagator(AbstractPropagator):
    def __init__(
            self,
            detector: Detector,
            photon_propagator: AbstractPhotonPropagator,
            name: str = "cascade",
            seed: int = defaults['seed'],
            resolution: float = 0.2,
            **kwargs
    ) -> None:
        super().__init__(
            detector=detector,
            photon_propagator=photon_propagator,
            seed=seed,
            name=name,
            **kwargs
        )
        self.resolution = resolution

    def _convert(self, event_records: EventRecords, k1: str) -> SourceRecords:
        source_records: List[SourceRecords] = []
        for index, event_record in event_records.df.iterrows():
            location = np.array(
                [
                    event_record.get('location_x'),
                    event_record.get('location_y'),
                    event_record.get('location_z'),
                ]
            )
            orientation = np.array(
                [
                    event_record.get('orientation_x'),
                    event_record.get('orientation_y'),
                    event_record.get('orientation_z'),
                ]
            )
            sources = make_realistic_cascade_source(
                location,
                event_record.time,
                orientation,
                event_record.energy,
                event_record.particle_id,
                key=k1,
                moliere_rand=True,
                resolution=self.resolution
            )
            event_source_records = self._convert_sources_to_source_records(
                event_record['event_id'],
                sources
            )
            source_records.append(event_source_records)

        return SourceRecords.concat(source_records)


class StartingTrackPropagator(TrackPropagator, CascadePropagator):
    def __init__(
            self,
            detector: Detector,
            photon_propagator: AbstractPhotonPropagator,
            name: str = "track_starting",
            seed: int = defaults['seed'],
            resolution: float = 0.2,
            **kwargs
    ) -> None:
        super(StartingTrackPropagator, self).__init__(
            detector=detector,
            photon_propagator=photon_propagator,
            name=name,
            seed=seed,
            resolution=resolution,
            **kwargs
        )
        self.rng = np.random.default_rng(seed)

    def propagate(self, event_records: EventRecords) -> Events:
        inelas = self.rng.uniform(1e-6, 1 - 1e-6)
        track_event_records = EventRecords(df=event_records.df.copy())
        cascade_event_records = EventRecords(df=event_records.df.copy())
        track_event_records.df.assign(energy=lambda x: inelas * x.energy)
        cascade_event_records.df.assign(energy=lambda x: (1 - inelas) * x.energy)

        track_event = super(TrackPropagator, self).propagate(track_event_records)
        cascade_event = super(CascadePropagator, self).propagate(cascade_event_records)

        return Events.concat([track_event, cascade_event])
