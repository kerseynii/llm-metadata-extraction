"""
OSM Data Fetcher for retrieving OpenStreetMap data via Overpass API.
"""

from typing import Optional, Dict, List, Union, Any
import overpy


class OSMDataFetcher:
    """Fetcher for OpenStreetMap data via Overpass API."""

    def __init__(self, api_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the OSM data fetcher.

        Args:
            api_url: The Overpass API endpoint URL. Uses default if None.
            timeout: Request timeout in seconds.
        """
        self.api = overpy.Overpass(url=api_url) if api_url else overpy.Overpass()
        self.timeout = timeout

    def query(self, query_string: str) -> overpy.Result:
        """
        Execute an Overpass API query.

        Args:
            query_string: The Overpass QL query string.

        Returns:
            Query result containing nodes, ways, and relations.
        """
        return self.api.query(query_string)

    def _build_tag_filter(self, tags: Optional[Dict[str, Any]] = None) -> str:
        """
        Build an Overpass tag filter string.

        Examples:
            {"amenity": "restaurant"} -> ["amenity"="restaurant"]
            {"building": True} -> ["building"]
            {"name": None} -> ["name"]

        Args:
            tags: Dictionary of OSM tags.

        Returns:
            A string suitable for Overpass QL.
        """
        if not tags:
            return ""

        tag_filter = ""
        for key, value in tags.items():
            if value is True or value is None:
                tag_filter += f'["{key}"]'
            else:
                tag_filter += f'["{key}"="{value}"]'

        return tag_filter

    def get_nodes_in_area(
        self,
        bbox: tuple[float, float, float, float],
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[overpy.Node]:
        """
        Get nodes in a bounding box with optional tag filters.

        Args:
            bbox: Bounding box as (south, west, north, east).
            tags: Dictionary of OSM tags to filter by.

        Returns:
            List of matching nodes.
        """
        south, west, north, east = bbox
        tag_filter = self._build_tag_filter(tags)

        query = f"""
        [out:json][timeout:{self.timeout}];
        node{tag_filter}({south},{west},{north},{east});
        out body;
        """

        result = self.query(query)
        return result.nodes

    def get_ways_in_area(
        self,
        bbox: tuple[float, float, float, float],
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[overpy.Way]:
        """
        Get ways in a bounding box with optional tag filters.

        Args:
            bbox: Bounding box as (south, west, north, east).
            tags: Dictionary of OSM tags to filter by.

        Returns:
            List of matching ways.
        """
        south, west, north, east = bbox
        tag_filter = self._build_tag_filter(tags)

        query = f"""
        [out:json][timeout:{self.timeout}];
        way{tag_filter}({south},{west},{north},{east});
        out body;
        >;
        out skel qt;
        """

        result = self.query(query)
        return result.ways

    def get_relations_in_area(
        self,
        bbox: tuple[float, float, float, float],
        tags: Optional[Dict[str, Any]] = None,
    ) -> List[overpy.Relation]:
        """
        Get relations in a bounding box with optional tag filters.

        Args:
            bbox: Bounding box as (south, west, north, east).
            tags: Dictionary of OSM tags to filter by.

        Returns:
            List of matching relations.
        """
        south, west, north, east = bbox
        tag_filter = self._build_tag_filter(tags)

        query = f"""
        [out:json][timeout:{self.timeout}];
        relation{tag_filter}({south},{west},{north},{east});
        out body;
        >;
        out skel qt;
        """

        result = self.query(query)
        return result.relations

    def get_buildings_in_area(
        self,
        bbox: tuple[float, float, float, float],
    ) -> List[Union[overpy.Node, overpy.Way, overpy.Relation]]:
        """
        Get all buildings in a bounding box.

        This fetches nodes, ways, and relations tagged with 'building'.
        Ways and relations are returned with center coordinates so they can
        be handled like point features in the rest of the app.

        Args:
            bbox: Bounding box as (south, west, north, east).

        Returns:
            Combined list of nodes, ways, and relations.
        """
        south, west, north, east = bbox

        query = f"""
        [out:json][timeout:{self.timeout}];
        (
          node["building"]({south},{west},{north},{east});
          way["building"]({south},{west},{north},{east});
          relation["building"]({south},{west},{north},{east});
        );
        out center tags;
        """

        result = self.query(query)

        # Attach center coordinates to ways
        for way in result.ways:
            if hasattr(way, "center_lat") and hasattr(way, "center_lon"):
                way.lat = float(way.center_lat)
                way.lon = float(way.center_lon)

        # Attach center coordinates to relations
        for relation in result.relations:
            if hasattr(relation, "center_lat") and hasattr(relation, "center_lon"):
                relation.lat = float(relation.center_lat)
                relation.lon = float(relation.center_lon)

        return list(result.nodes) + list(result.ways) + list(result.relations)