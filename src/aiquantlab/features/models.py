"""Serializable contracts for causal research features."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FeatureFamily(StrEnum):
    PRICE_STRUCTURE = "price_structure"


class FeatureOutputDType(StrEnum):
    BOOLEAN = "boolean"
    FLOAT64 = "float64"


class FeatureParameter(BaseModel):
    """One immutable, JSON-serializable feature parameter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    value: int | float | str | bool


class FeatureSpec(BaseModel):
    """Declarative definition of one causal, interpretable feature."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    family: FeatureFamily
    input_columns: tuple[str, ...] = Field(min_length=1)
    parameters: tuple[FeatureParameter, ...] = ()
    lookback_bars: int = Field(ge=0)
    uses_current_bar: bool
    warm_up_bars: int = Field(ge=0)
    output_dtype: FeatureOutputDType
    economic_meaning: str = Field(min_length=10)
    leakage_notes: str = Field(min_length=10)

    @field_validator("input_columns")
    @classmethod
    def input_columns_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("input_columns must be unique")
        return value

    @field_validator("parameters")
    @classmethod
    def parameter_names_must_be_unique(
        cls,
        value: tuple[FeatureParameter, ...],
    ) -> tuple[FeatureParameter, ...]:
        names = [parameter.name for parameter in value]
        if len(set(names)) != len(names):
            raise ValueError("parameter names must be unique")
        return value

    @model_validator(mode="after")
    def warm_up_must_cover_lookback(self) -> Self:
        if self.warm_up_bars < self.lookback_bars:
            raise ValueError("warm_up_bars must be at least lookback_bars")
        return self

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class FeatureBundle(BaseModel):
    """Immutable, ordered collection of registered FeatureSpec objects."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,63}$")
    revision: int = Field(default=1, ge=1)
    features: tuple[FeatureSpec, ...] = Field(min_length=1)

    @field_validator("features")
    @classmethod
    def feature_names_must_be_unique(
        cls,
        value: tuple[FeatureSpec, ...],
    ) -> tuple[FeatureSpec, ...]:
        names = [feature.name for feature in value]
        if len(set(names)) != len(names):
            raise ValueError("feature names must be unique within a bundle")
        return value

    @property
    def warm_up_bars(self) -> int:
        return max(feature.warm_up_bars for feature in self.features)

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(feature.name for feature in self.features)

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class FeatureManifest(BaseModel):
    """Provenance and integrity record for one feature materialization run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    output_file: str
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    row_count: int = Field(ge=0)
    source_ohlcv_file: str
    source_ohlcv_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_bundle: FeatureBundle
    feature_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_columns: tuple[str, ...]
    validity_column: str
    code_version: str = Field(min_length=1)
    warm_up_bars: int = Field(ge=0)
    mtf_sources: tuple[str, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def fingerprints_must_match_embedded_bundle(self) -> Self:
        if self.feature_bundle_sha256 != self.feature_bundle.fingerprint():
            raise ValueError("feature_bundle_sha256 does not match feature_bundle")
        if self.feature_columns != self.feature_bundle.feature_names:
            raise ValueError("feature_columns do not match feature_bundle")
        if self.warm_up_bars != self.feature_bundle.warm_up_bars:
            raise ValueError("warm_up_bars does not match feature_bundle")
        return self
