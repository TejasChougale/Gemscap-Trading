<mxfile host="app.diagrams.net" agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36" version="29.2.4">
  <diagram id="gemscap-flow" name="Gemscap-Trading Flowchart">
    <mxGraphModel dx="1892" dy="1627" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="g_inputs" connectable="0" parent="1" style="group" value="Inputs" vertex="1">
          <mxGeometry height="150" width="420" x="20" y="10" as="geometry" />
        </mxCell>
        <mxCell id="A1" parent="g_inputs" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6A500;fontSize=12;" value="Market Data Sources&#xa;(Websocket / REST / Files)" vertex="1">
          <mxGeometry height="50" width="300" x="10" y="10" as="geometry" />
        </mxCell>
        <mxCell id="A2" parent="g_inputs" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6A500;fontSize=12;" value="User / Config&#xa;(settings, thresholds)" vertex="1">
          <mxGeometry height="50" width="300" x="10" y="75" as="geometry" />
        </mxCell>
        <mxCell id="lbl_inputs" parent="g_inputs" style="text;html=1;fontSize=12;fontStyle=1;align=left;" value="Inputs" vertex="1">
          <mxGeometry height="20" width="100" x="5" y="-16" as="geometry" />
        </mxCell>
        <mxCell id="e_B2_C2" edge="1" parent="g_inputs" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="160" y="150" />
            </Array>
            <mxPoint x="460" y="150" as="sourcePoint" />
            <mxPoint x="160" y="315" as="targetPoint" />
          </mxGeometry>
        </mxCell>
        <mxCell id="g_ingest" connectable="0" parent="1" style="group" value="Ingestion" vertex="1">
          <mxGeometry height="160" width="420" x="470" as="geometry" />
        </mxCell>
        <mxCell id="B2" parent="g_ingest" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF0F0;strokeColor=#D9534F;fontSize=12;" value="Validator / Preprocessor&#xa;(timestamps, ordering)" vertex="1">
          <mxGeometry height="50" width="300" x="5" y="50" as="geometry" />
        </mxCell>
        <mxCell id="lbl_ingest" parent="g_ingest" style="text;html=1;fontSize=12;fontStyle=1;align=left;" value="Ingestion" vertex="1">
          <mxGeometry height="20" width="100" x="5" y="-16" as="geometry" />
        </mxCell>
        <mxCell id="e_A2_D2" edge="1" parent="g_ingest" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="160" y="110" />
            </Array>
            <mxPoint x="-140" y="110" as="sourcePoint" />
            <mxPoint x="160" y="285" as="targetPoint" />
          </mxGeometry>
        </mxCell>
        <mxCell id="g_processing" connectable="0" parent="1" style="group" value="Processing" vertex="1">
          <mxGeometry height="280" width="820" x="30" y="210" as="geometry" />
        </mxCell>
        <mxCell id="C1" parent="g_processing" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F6FF;strokeColor=#2B8BD3;fontSize=12;" value="resampling.py&#xa;(ticks → OHLC candles)" vertex="1">
          <mxGeometry height="50" width="300" x="10" y="10" as="geometry" />
        </mxCell>
        <mxCell id="AGs5mc6eRlokDfLKgDxu-1" edge="1" parent="g_processing" source="C2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=1;exitY=0.5;exitDx=0;exitDy=0;">
          <mxGeometry relative="1" as="geometry">
            <mxPoint x="330" y="150" as="targetPoint" />
          </mxGeometry>
        </mxCell>
        <mxCell id="C2" parent="g_processing" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F6FF;strokeColor=#2B8BD3;fontSize=12;" value="analytics.py&#xa;(indicators, rolling stats)" vertex="1">
          <mxGeometry height="50" width="300" x="10" y="75" as="geometry" />
        </mxCell>
        <mxCell id="lbl_proc" parent="g_processing" style="text;html=1;fontSize=12;fontStyle=1;align=left;" value="Processing" vertex="1">
          <mxGeometry height="20" width="100" x="5" y="-16" as="geometry" />
        </mxCell>
        <mxCell id="g_persist" connectable="0" parent="g_processing" style="group" value="Persistence" vertex="1">
          <mxGeometry height="140" width="870" x="-50" y="140" as="geometry" />
        </mxCell>
        <mxCell id="E1" parent="g_persist" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F3E8FF;strokeColor=#7A39D4;fontSize=12;" value="storage.py&#xa;(CSV / file storage)" vertex="1">
          <mxGeometry height="50" width="300" x="10" y="10" as="geometry" />
        </mxCell>
        <mxCell id="E2" parent="g_persist" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F3E8FF;strokeColor=#7A39D4;fontSize=12;" value="Optional DB / Time-series DB" vertex="1">
          <mxGeometry height="50" width="300" x="330" y="10" as="geometry" />
        </mxCell>
        <mxCell id="lbl_persist" parent="g_persist" style="text;html=1;fontSize=12;fontStyle=1;align=left;" value="Persistence" vertex="1">
          <mxGeometry height="20" width="120" x="5" y="-16" as="geometry" />
        </mxCell>
        <mxCell id="e_E1_E2" edge="1" parent="g_persist" source="E1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;endArrow=block;dashed=1;" target="E2">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_C1_E1" edge="1" parent="g_processing" source="C1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;dashed=1;" target="E1">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="150" y="80" />
              <mxPoint x="150" y="80" />
            </Array>
          </mxGeometry>
        </mxCell>
        <mxCell id="e_C2_E1" edge="1" parent="g_processing" source="C2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;dashed=1;" target="E1">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="150" y="140" />
              <mxPoint x="150" y="140" />
            </Array>
          </mxGeometry>
        </mxCell>
        <mxCell id="g_actions" connectable="0" parent="1" style="group" value="Actions" vertex="1">
          <mxGeometry height="200" width="420" x="670" y="120" as="geometry" />
        </mxCell>
        <mxCell id="D1" parent="g_actions" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E8FFE6;strokeColor=#3C9A2B;fontSize=12;" value="alerts.py&#xa;(thresholds, dispatchers)" vertex="1">
          <mxGeometry height="50" width="300" x="10" y="10" as="geometry" />
        </mxCell>
        <mxCell id="lbl_actions" parent="g_actions" style="text;html=1;fontSize=12;fontStyle=1;align=left;" value="Actions" vertex="1">
          <mxGeometry height="20" width="100" x="5" y="-16" as="geometry" />
        </mxCell>
        <mxCell id="D2" parent="g_actions" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E8FFE6;strokeColor=#3C9A2B;fontSize=12;" value="app.py&#xa;(orchestrator / runner)" vertex="1">
          <mxGeometry height="50" width="300" x="30" y="105" as="geometry" />
        </mxCell>
        <mxCell id="UserExt" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#999999;fontSize=12;" value="User / External Channels" vertex="1">
          <mxGeometry height="40" width="160" x="730" y="430" as="geometry" />
        </mxCell>
        <mxCell id="e_A1_B1" edge="1" parent="1" source="A1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" target="B1">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_B1_B2" edge="1" parent="1" source="B1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" target="B2">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_B2_C1" edge="1" parent="1" source="B2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" target="C1">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="630" y="160" />
              <mxPoint x="180" y="160" />
            </Array>
          </mxGeometry>
        </mxCell>
        <mxCell id="e_C2_D2" edge="1" parent="1" source="C2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" target="D2">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e_C2_D1" edge="1" parent="1" source="C2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;" target="D1">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="830" y="310" />
            </Array>
          </mxGeometry>
        </mxCell>
        <mxCell id="e_D1_User" edge="1" parent="1" source="D1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;edgeLabelBackground=1;labelPosition=center;verticalLabelPosition=middle;html=1;strokeColor=#000000;" target="UserExt">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="630" y="340" />
              <mxPoint x="810" y="340" />
            </Array>
          </mxGeometry>
        </mxCell>
        <mxCell id="e_D2_E1" edge="1" parent="1" source="D2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;dashed=1;" target="E1">
          <mxGeometry relative="1" as="geometry">
            <Array as="points">
              <mxPoint x="180" y="270" />
            </Array>
          </mxGeometry>
        </mxCell>
        <mxCell id="B1" parent="1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF0F0;strokeColor=#D9534F;fontSize=12;" value="backend.py&#xa;(data connectors &amp; replay)" vertex="1">
          <mxGeometry height="50" width="300" x="475" y="-11" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
