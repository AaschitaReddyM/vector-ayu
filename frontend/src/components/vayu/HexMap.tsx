import { useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import { MOCK_PATIENTS, MOCK_RISK_SCORES } from "@/lib/mock-data";

export function HexMapPlaceholder() {
  const isNewDelhi = typeof window !== "undefined" && localStorage.getItem("vayu_region") === "new_delhi";
  const center: [number, number] = isNewDelhi ? [28.6139, 77.2090] : [32.7767, -96.797];

  // Generate random lat/lng around DFW for our mock patients based on their index
  // so the markers are stable between renders
  const markers = useMemo(() => {
    return MOCK_PATIENTS.map((p, i) => {
      // Deterministic offset based on index to spread them around DFW
      const latOffset = Math.sin(i * 1.5) * 0.2;
      const lngOffset = Math.cos(i * 2.3) * 0.3;

      const riskScore = MOCK_RISK_SCORES.find((r) => r.patient_id === p.id);
      const risk = riskScore
        ? Math.max(riskScore.probabilities.respiratory, riskScore.probabilities.cardiovascular)
        : 0.1;

      let color = "#00d4aa"; // low risk
      if (isNewDelhi) {
        // Toxic AQI gradient for New Delhi
        color = "#ffb347"; // Yellow (Unhealthy for sensitive)
        if (risk > 0.6) color = "#ff6b6b"; // Red (Unhealthy)
        if (risk > 0.8) color = "#9b5de5"; // Deep Purple (Severe/Hazardous)
      } else {
        // Heat/Wildfire gradient for Dallas
        color = "#00d4aa"; // Teal (Good)
        if (risk > 0.6) color = "#ffb347"; // Amber (Elevated)
        if (risk > 0.8) color = "#ff6b6b"; // Coral (High)
      }

      return {
        id: p.id,
        name: `${p.given_name} ${p.family_name}`,
        lat: center[0] + latOffset,
        lng: center[1] + lngOffset,
        risk: risk,
        color: color,
      };
    });
  }, [center]);

  return (
    <div className="relative w-full h-[350px] rounded-[14px] overflow-hidden border border-border">
      <MapContainer
        center={center}
        zoom={10}
        scrollWheelZoom={true}
        style={{ width: "100%", height: "100%", background: "#0a0f1e" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="map-tiles"
        />

        {markers.map((m) => (
          <CircleMarker
            key={m.id}
            center={[m.lat, m.lng]}
            radius={m.risk > 0.8 ? 12 : 8}
            pathOptions={{
              fillColor: m.color,
              fillOpacity: 0.7,
              color: m.risk > 0.8 ? "#fff" : "transparent",
              weight: 2,
            }}
          >
            <Tooltip>
              <div className="font-sans">
                <div className="font-bold text-[14px]">
                  {m.name} ({m.id})
                </div>
                <div className="text-[12px] opacity-80">
                  Risk Level: {(m.risk * 100).toFixed(1)}%
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
