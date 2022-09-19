import requests
import tqdm

import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from typing import List, Dict, Any, Tuple, Optional, NamedTuple, Union, NewType


FTP_HOSTED_URL = "https://fromthepage.com"


FtpFieldBasedTranscription = NewType(
    "FtpFieldBasedTranscription", List[Optional[Dict[str, str]]]
)


@dataclass
class FtpInstance:
    url: str

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")

    def request_projects(
        self, slug: str, session: requests.Session
    ) -> "FtpProjectCollection":
        response = session.get(f"{self.url}/iiif/collections/{slug}")
        response.raise_for_status()
        projects = FtpProjectCollection.from_json(response.json())
        return projects


@dataclass
class FtpProjectCollection:
    url: str
    projects: List["FtpProject"] = field(default_factory=list)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpProjectCollection":
        return cls(
            url=json["@id"],
            projects=[
                FtpProject(url=collection["@id"], label=collection["label"])
                for collection in json["collections"]
            ],
        )

    def request_project(self, label: str, session: requests.Session) -> "FtpProject":
        for project in self.projects:
            if project.label == label:
                project.request(session=session)
                return project
        raise KeyError(repr(label))


@dataclass
class FtpProject:
    url: str
    label: Optional[str] = None
    works: List["FtpWork"] = field(default_factory=list)
    instance_url: str = field(init=False)
    project_id: str = field(init=False)

    def __post_init__(self):
        self.instance_url, self.project_id = parse_ftp_collection_url(self.url)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpProject":
        project = cls(url=json["@id"])
        project._load(json)
        return project

    @classmethod
    def from_url(cls, url: str, session: requests.Session) -> "FtpProject":
        project = cls(url=url)
        project.request(session=session)
        return project

    def request(self, session: requests.Session) -> None:
        response = session.get(self.url)
        response.raise_for_status()
        json = response.json()
        self._load(json)

    def _load(self, json: Dict[str, Any]) -> None:
        self.url = json["@id"]
        self.__post_init__()
        self.label = json["label"]
        self.works = [FtpWork.from_json(manifest) for manifest in json["manifests"]]

    def request_works(
        self, session: requests.Session, show_progress: bool = True
    ) -> None:
        works = tqdm.tqdm(self.works) if show_progress else self.works
        for work in works:
            work.request(session=session)

    def request_work_structured_data_config(
        self, session: requests.Session
    ) -> "FtpStructuredDataConfig":
        return _request_structured_data_configuration(
            instance_url=self.instance_url,
            project_id=self.project_id,
            level="work",
            session=session,
        )

    def request_page_structured_data_config(
        self, session: requests.Session
    ) -> "FtpStructuredDataConfig":
        return _request_structured_data_configuration(
            instance_url=self.instance_url,
            project_id=self.project_id,
            level="page",
            session=session,
        )


def _request_structured_data_configuration(
    instance_url: str, project_id: str, level: str, session: requests.Session
) -> "FtpStructuredDataConfig":
    response = session.get(
        f"{instance_url}/iiif/{project_id}/structured/config/{level}"
    )
    response.raise_for_status()
    return FtpStructuredDataConfig.from_json(response.json())


@dataclass
class FtpStructuredDataConfig:
    url: str
    label: str
    fields: List["FtpStructuredDataFieldConfig"] = field(default_factory=list)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpStructuredDataConfig":
        return cls(
            url=json["@id"],
            label=json["label"],
            fields=[
                FtpStructuredDataFieldConfig.from_json(field_config)
                for field_config in json["config"]
            ],
        )


class FtpStructuredDataFieldConfig(NamedTuple):
    label: str
    input_type: str
    position: int
    line: int
    url: str
    options: List[str]

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpStructuredDataFieldConfig":
        return cls(
            url=json["@id"],
            label=json["label"],
            input_type=json["input_type"],
            position=int(json["position"]),
            line=int(json["line"]),
            options=json.get("options", []),
        )


@dataclass
class FtpWork:
    url: str
    label: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    read_url: Optional[str] = None
    contents_url: Optional[str] = None
    renderings: List["FtpRendering"] = field(default_factory=list)
    pages: List["FtpPage"] = field(default_factory=list)
    cdm_instance_url: Optional[str] = None
    cdm_collection_alias: Optional[str] = None
    cdm_object_dmrecord: Optional[str] = None

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpWork":
        work = cls(url=json["@id"])
        work._load(json)
        return work

    @classmethod
    def from_url(cls, url: str, session: requests.Session) -> "FtpWork":
        work = cls(url=url)
        work.request(session=session)
        return work

    def request(self, session: requests.Session) -> None:
        response = session.get(self.url)
        response.raise_for_status()
        json = response.json()
        self._load(json)

    def _load(self, json: Dict[str, Any]) -> None:
        # Update everything based on the new data
        self.url = json["@id"]
        self.label = json["label"]
        self.read_url = None
        self.contents_url = None
        self.metadata = {}
        self.renderings = []
        self.pages = []
        self.cdm_instance_url = None
        self.cdm_collection_alias = None
        self.cdm_object_dmrecord = None

        metadata = json.get("metadata")
        if metadata is not None:
            self.metadata = {pair["label"]: pair["value"] for pair in metadata}

        related = json.get("related")
        if related is not None:
            self.read_url = related[0]["@id"]
            self.contents_url = related[1]["@id"]

        # TODO: conflating seeAlso and renderings duplicates Verbatim Plaintext: problem or not?
        seeAlsos = json.get("seeAlso")
        if seeAlsos is not None:
            for seeAlso in seeAlsos:
                self.renderings.append(FtpRendering.from_json(seeAlso))

        sequences = json.get("sequences")
        if sequences is not None:
            sequence = sequences[0]
            for rendering in sequence["rendering"]:
                self.renderings.append(FtpRendering.from_json(rendering))
            self.pages = [FtpPage.from_json(canvas) for canvas in sequence["canvases"]]

        if "dc:source" in self.metadata:
            cdm_iiif_manifest_url = self.metadata["dc:source"]

            # Handle "dc:source" URLs that are somehow in lists with null strings
            if isinstance(cdm_iiif_manifest_url, list):
                for obj in cdm_iiif_manifest_url:
                    if isinstance(obj, str) and obj.startswith("http"):
                        cdm_iiif_manifest_url = obj
                        break
                else:
                    raise ValueError("malformed dc:source metadata field")

            (
                self.cdm_instance_url,
                self.cdm_collection_alias,
                self.cdm_object_dmrecord,
            ) = parse_cdm_iiif_manifest_url(cdm_iiif_manifest_url)

    def _get_rendering(self, attr: str, value: str) -> "FtpRendering":
        for rendering in self.renderings:
            if getattr(rendering, attr) == value:
                return rendering
        raise KeyError(repr(value))

    def request_rendering(self, label: str, session: requests.Session) -> str:
        response = session.get(self._get_rendering(attr="label", value=label).url)
        response.raise_for_status()
        return response.text

    def request_transcript_fields(
        self,
        session: requests.Session,
        label: str = "XHTML Export",
        empty_page_is_none: bool = True,
    ) -> FtpFieldBasedTranscription:
        raw_rendering = self.request_rendering(label=label, session=session)
        field_based_transcription = RENDERING_EXTRACTORS[label](raw_rendering)
        if empty_page_is_none:
            return [
                fields if fields and any(fields.values()) else None
                for fields in field_based_transcription
            ]
        return field_based_transcription

    def request_structured_data(self, session: requests.Session) -> "FtpStructuredData":
        for rendering in self.renderings:
            if rendering.context and rendering.context.endswith(
                "/jsonld/structured/1/context.json"
            ):
                url = rendering.url
                break
        else:
            raise KeyError("couldn't find work structured data rendering")
        response = session.get(url)
        response.raise_for_status()
        return FtpStructuredData.from_json(response.json())


class FtpRendering(NamedTuple):
    url: str
    label: str
    profile: str
    format_: Optional[str] = None
    context: Optional[str] = None

    @classmethod
    def from_json(cls, json: Dict[str, str]) -> "FtpRendering":
        return cls(
            url=json["@id"],
            label=json["label"],
            format_=json.get("format"),
            profile=json["profile"],
            context=json.get("@context"),
        )


@dataclass
class FtpPage:
    id_: str
    label: Optional[str] = None
    read_url: Optional[str] = None
    transcribe_url: Optional[str] = None
    renderings: List[FtpRendering] = field(default_factory=list)
    cdm_instance_url: Optional[str] = None
    cdm_collection_alias: Optional[str] = None
    cdm_page_dmrecord: Optional[str] = None

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpPage":
        id_ = json["@id"]
        (
            cdm_instance_url,
            cdm_collection_alias,
            cdm_page_dmrecord,
        ) = parse_ftp_canvas_id(id_)
        return cls(
            id_=id_,
            label=json["label"],
            read_url=json["related"][0]["@id"],
            transcribe_url=json["related"][1]["@id"],
            renderings=[FtpRendering.from_json(seeAlso) for seeAlso in json["seeAlso"]],
            cdm_instance_url=cdm_instance_url,
            cdm_collection_alias=cdm_collection_alias,
            cdm_page_dmrecord=cdm_page_dmrecord,
        )

    def request_transcript(self, label: str, session: requests.Session) -> str:
        response = session.get(self._get_rendering(attr="label", value=label).url)
        response.raise_for_status()
        return response.text

    def _get_rendering(self, attr: str, value: str) -> FtpRendering:
        for rendering in self.renderings:
            if getattr(rendering, attr) == value:
                return rendering
        raise KeyError(repr(value))

    def request_structured_data(self, session: requests.Session) -> "FtpStructuredData":
        for rendering in self.renderings:
            if rendering.context and rendering.context.endswith(
                "/jsonld/structured/1/context.json"
            ):
                break
        else:
            raise KeyError("couldn't find page structured data rendering")
        response = session.get(rendering.url)
        response.raise_for_status()
        return FtpStructuredData.from_json(response.json())


@dataclass
class FtpStructuredData:
    contributors: List[Dict[str, str]] = field(default_factory=list)
    data: List["FtpStructuredDataField"] = field(default_factory=list)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FtpStructuredData":
        return cls(
            contributors=json["contributors"],
            data=[FtpStructuredDataField(**field_data) for field_data in json["data"]],
        )


class FtpStructuredDataField(NamedTuple):
    label: str
    value: Union[str, List[str]]
    config: str


def parse_ftp_collection_url(url: str) -> Tuple[str, str]:
    instance_url, _, collection_id = url.partition("/iiif/collection/")
    return instance_url, collection_id


def parse_cdm_iiif_manifest_url(url: str) -> Tuple[str, str, str]:
    # New route: .../iiif/2/p15808coll19:872/manifest.json
    # Old route: .../iiif/info/p15808coll19/3001/manifest.json
    cdm_instance_url = "://".join(urlsplit(url)[:2])
    match = re.search(r"/([^/:]*)[/:](\d*)/manifest.json", url)
    if match is None:
        raise ValueError(repr(url))
    return (cdm_instance_url, *match.groups())


def parse_ftp_canvas_id(id_: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    match = re.match(r"(https?://[^/]*)/.*/([^/:]*)[/:](\d*)/canvas/c\d+", id_)
    if match:
        return match.groups()
    return (None, None, None)


def request_ftp_project(
    instance_url: str, slug: str, project_label: str, session: requests.Session
) -> FtpProject:
    instance = FtpInstance(url=instance_url)
    projects = instance.request_projects(slug=slug, session=session)
    return projects.request_project(label=project_label, session=session)


def request_ftp_project_and_works(
    instance_url: str,
    slug: str,
    project_label: str,
    session: requests.Session,
    show_progress: bool = True,
) -> FtpProject:
    project = request_ftp_project(
        instance_url=instance_url,
        slug=slug,
        project_label=project_label,
        session=session,
    )
    project.request_works(session=session, show_progress=show_progress)
    return project


def extract_fields_from_tei(tei: str) -> FtpFieldBasedTranscription:
    NS = {"ns": "http://www.tei-c.org/ns/1.0"}
    tei_root = ET.fromstring(tei)
    tei_pages = tei_root.findall("./ns:text/ns:body/ns:div", namespaces=NS)
    pages = []
    for tei_page in tei_pages:
        tei_fields = tei_page.findall("ns:p", namespaces=NS)
        fields = extract_fields_from_p_span_xml(tei_fields, namespaces=NS)
        pages.append(fields)
    return pages


def extract_fields_from_xhtml(xhtml: str) -> FtpFieldBasedTranscription:
    NS = {"ns": "http://www.w3.org/1999/xhtml"}
    # The FromThePage XHTML Export isn't valid XHTML because of the JS blob on line 6
    html_no_scripts = re.sub(r"<script>?.*</script>", "", xhtml).strip()
    html_root = ET.fromstring(html_no_scripts)
    html_pages = html_root.findall(
        "ns:body/ns:div[@class='pages']/ns:div", namespaces=NS
    )
    pages = []
    for html_page in html_pages:
        html_fields = html_page.findall(
            "ns:div[@class='page-content']/ns:p", namespaces=NS
        )
        fields = extract_fields_from_p_span_xml(html_fields, namespaces=NS)
        pages.append(fields)
    return pages


def extract_fields_from_p_span_xml(
    xml_ps: List[ET.Element], namespaces: Dict[str, str]
) -> Optional[Dict[str, str]]:
    fields = dict()
    last_label: Optional[str] = None
    for xml_p in xml_ps:
        label = xml_p.find("ns:span", namespaces=namespaces)
        # Element truthiness is on existence of child Elements, so test for None
        if label is not None:
            label_text = last_label = removesuffix(label.text, ": ")
            fields[label_text] = "".join(list(xml_p.itertext())[1:]).strip()
        else:
            fields[last_label] = "\n\n".join(
                [fields[last_label], "".join(xml_p.itertext())]
            ).strip()
    return fields or None


RENDERING_EXTRACTORS = {
    "XHTML Export": extract_fields_from_xhtml,
    "TEI Export": extract_fields_from_tei,
}


def removesuffix(s: str, suffix: str) -> str:
    if s.endswith(suffix):
        return s[: -len(suffix)]
    return s
