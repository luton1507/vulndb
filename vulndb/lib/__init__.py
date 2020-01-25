from abc import ABCMeta, abstractmethod

import dataclasses
from datetime import datetime
from enum import Enum

import json
import re


# Known application package types
KNOWN_PKG_TYPES = ["composer", "maven", "npm", "nuget", "pypi", "rubygems", "golang"]

# CPE Regex
CPE_REGEX = re.compile(
    "cpe:?:[^:]+:[^:]+:(?P<vendor>[^:]+):(?P<package>[^:]+):(?P<version>[^:]+)"
)


class VulnerabilitySource(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def download_all():
        pass

    @classmethod
    @abstractmethod
    def download_recent():
        pass

    @classmethod
    @abstractmethod
    def convert(data):
        pass

    @classmethod
    @abstractmethod
    def store(data):
        pass

    @classmethod
    @abstractmethod
    def refresh():
        pass


class Severity(str, Enum):
    UNSPECIFIED: str = "UNSPECIFIED"
    LOW: str = "LOW"
    MEDIUM: str = "MEDIUM"
    HIGH: str = "HIGH"
    CRITICAL: str = "CRITICAL"

    @staticmethod
    def from_str(sevstr):
        if isinstance(sevstr, dict):
            sevstr = sevstr["value"]
        if not sevstr:
            return Severity.UNSPECIFIED
        for k, v in Severity.__members__.items():
            if k == sevstr.upper():
                return v
        return Severity.UNSPECIFIED

    def __str__(self):
        return self.value


def convert_time(time_str):
    """Convert iso string to date time object

    :param time_str: String time to convert
    """
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%Mz")
        return dt
    except Exception:
        return time_str


class Vulnerability(object):
    """Vulnerability
    """

    def __init__(
        self,
        vid,
        problem_type,
        score,
        severity,
        description,
        related_urls,
        details,
        cvss_v3,
        source_update_time,
    ):
        self.id = vid
        self.problem_type = problem_type
        self.score = score
        self.severity = Severity.from_str(severity)
        self.description = description
        self.related_urls = related_urls
        self.details = details
        self.cvss_v3 = cvss_v3
        self.source_update_time: datetime = convert_time(source_update_time)

    def __repr__(self):
        return json.dumps(
            {
                "id": self.id,
                "problem_type": self.problem_type,
                "score": self.score,
                "severity": self.severity.value,
                "description": self.description,
                "related_urls": self.related_urls,
                "details": str(self.details),
                "cvss_v3": str(self.cvss_v3),
                "source_update_time": self.source_update_time.isoformat()
                if isinstance(self.source_update_time, datetime)
                else self.source_update_time,
            }
        )


class VulnerabilityDetail(object):
    """Vulnerability detail class
    """

    def __init__(
        self,
        cpe_uri,
        package,
        min_affected_version,
        max_affected_version,
        severity,
        description,
        fixed_location,
        package_type,
        is_obsolete,
        source_update_time,
    ):
        parts = CPE_REGEX.match(cpe_uri)
        self.cpe_uri = cpe_uri
        self.package = package if package else parts.group("package")
        self.min_affected_version = (
            min_affected_version if min_affected_version else parts.group("version")
        )
        self.max_affected_version = (
            max_affected_version if max_affected_version else parts.group("version")
        )
        self.severity = Severity.from_str(severity)
        self.description = description
        self.fixed_location = VulnerabilityLocation.from_dict(cpe_uri, fixed_location)
        self.package_type = VulnerabilityDetail.get_type(cpe_uri, package_type)
        self.is_obsolete = is_obsolete
        self.source_update_time: datetime = convert_time(source_update_time)

    @staticmethod
    def get_type(cpe_uri, package_type):
        if package_type in KNOWN_PKG_TYPES:
            return package_type
        parts = CPE_REGEX.match(cpe_uri)
        if parts:
            type = parts.group("vendor")
            if type in KNOWN_PKG_TYPES:
                return type
            else:
                # Unknown type. Just pass-through for now
                return type
        else:
            return None

    @staticmethod
    def from_dict(detail):
        return VulnerabilityDetail(
            detail.get("cpe_uri"),
            detail.get("package"),
            detail.get("min_affected_version"),
            detail.get("max_affected_version"),
            detail.get("severity"),
            detail.get("description"),
            detail.get("fixed_location"),
            detail.get("package_type"),
            detail.get("is_obsolete"),
            detail.get("source_update_time"),
        )


class PackageIssue(object):
    """Package issue class
    """

    def __init__(self, affected_location, fixed_location):
        self.affected_location = VulnerabilityLocation.from_dict(
            affected_location, None
        )
        self.fixed_location = VulnerabilityLocation.from_dict(fixed_location, None)

    @staticmethod
    def from_dict(package_issue):
        return PackageIssue(
            package_issue.get("affected_location"), package_issue.get("fixed_location")
        )

    def __str__(self):
        return json.dumps(
            {
                "affected_location": str(self.affected_location),
                "fixed_location": str(self.fixed_location),
            }
        )


@dataclasses.dataclass
class CvssV3(object):
    """CVSS v3 representation
    """

    base_score: float
    exploitability_score: float
    impact_score: float
    attack_vector: str
    attack_complexity: str
    privileges_required: str
    user_interaction: str
    scope: str
    confidentiality_impact: str
    integrity_impact: str
    availability_impact: str


@dataclasses.dataclass
class VulnerabilityLocation(object):
    cpe_uri: str
    package: str
    version: str

    @staticmethod
    def from_dict(cpe_uri, fixed_location):
        if not fixed_location:
            return None
        parts = CPE_REGEX.match(cpe_uri)
        if parts:
            return VulnerabilityLocation(fixed_location, parts.group(2), parts.group(3))
        else:
            return None


@dataclasses.dataclass
class VulnerabilityOccurrence:
    """Class to represent an occurence of a vulnerability
    """

    id: str
    problem_type: str
    type: str
    severity: Severity
    cvss_score: str
    package_issue: PackageIssue
    short_description: str
    long_description: str
    related_urls: list
    effective_severity: Severity

    def to_dict(self):
        """Convert the object to dict
        """
        return {
            "id": self.id,
            "problem_type": self.problem_type,
            "type": self.type,
            "severity": str(self.severity),
            "cvss_score": str(self.cvss_score),
            "package_issue": str(self.package_issue),
            "short_description": self.short_description,
            "long_description": self.long_description,
            "related_urls": self.related_urls,
            "effective_severity": str(self.effective_severity),
        }