"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MatchdayPoints } from "@/lib/api/types";

export function PointsChart({ data }: { data: MatchdayPoints[] }) {
  return <div className="h-72 w-full" aria-label="Punkte je Spieltag">
    <ResponsiveContainer>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#232848" vertical={false}/>
        <XAxis dataKey="matchday" tick={{ fill: "#5D6491", fontSize: 11 }} axisLine={false} tickLine={false}/>
        <YAxis allowDecimals={false} tick={{ fill: "#5D6491", fontSize: 11 }} axisLine={false} tickLine={false}/>
        <Tooltip contentStyle={{ background: "#171B33", border: "1px solid #232848", borderRadius: 12 }} labelFormatter={(value) => `Spieltag ${value}`} formatter={(value) => [value, "Punkte"]}/>
        <ReferenceLine y={0} stroke="#5D6491"/>
        <Bar dataKey="points" fill="#6E9BFF" name="Punkte"/>
      </BarChart>
    </ResponsiveContainer>
  </div>;
}
