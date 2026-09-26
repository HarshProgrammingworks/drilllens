import { CircleMarker, MapContainer, Popup, Polyline, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export interface MapWell {
  id: string;
  well_id: string;
  well_name: string;
  latitude: number;
  longitude: number;
  distance_km?: number;
  depth?: number | null;
  formation?: string | null;
  status?: string;
  risk?: string;
  kind: "current" | "nearby" | "historical" | "risk";
}

const COLOR = { current: "#d4a017", nearby: "#3d8bfd", historical: "#3d8bfd", risk: "#d64545" };

export function WellMap({ wells, trajectories, tileUrl }: { wells: MapWell[]; trajectories?: Array<{ id: string; positions: [number, number][] }>; tileUrl: string }) {
  const currentWell = wells.find((well) => well.kind === "current");
  const center: [number, number] = currentWell ? [currentWell.latitude, currentWell.longitude] : [22.5937, 78.9629];
  const zoom = currentWell ? 9 : 5;
  return (
    <div className="h-[560px] panel overflow-hidden">
      <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }}>
        <TileLayer attribution='&copy; OpenStreetMap' url={tileUrl} />
        {trajectories?.map((line) => <Polyline key={line.id} positions={line.positions} pathOptions={{ color: "#3d8bfd", weight: 2 }} />)}
        {wells.map((well) => (
          <CircleMarker key={well.id + well.kind} center={[well.latitude, well.longitude]} radius={well.kind === "current" ? 10 : 7} pathOptions={{ color: COLOR[well.kind], fillOpacity: 0.85 }}>
            <Popup>
              <div className="text-sm text-black">
                <strong>{well.well_name}</strong>
                <div>Well ID {well.well_id}</div>
                {well.distance_km != null && <div>Distance {well.distance_km} km</div>}
                <div>Depth {well.depth ?? "—"} m</div>
                <div>Formation {well.formation || "—"}</div>
                <div>Status {well.status || "—"}</div>
                <div>Risk {well.risk || "—"}</div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
