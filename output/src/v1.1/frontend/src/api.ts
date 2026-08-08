import { sampleRecommendations, type Recommendation } from "./data";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

interface ApiRecommendationCard {
  recommendation_id: string;
  menu_name: string;
  place_name: string;
  distance_m: number;
  walk_minutes: number;
  reason_line: string;
  confidence_score: number;
  context_tags: string[];
  signature_menu?: string | null;
  price?: number | null;
  address?: string | null;
  reason_detail?: string | null;
}

export async function fetchRecommendations(signal?: AbortSignal): Promise<Recommendation[]> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ member_id: "demo-member", region_label: "강남역 근처" }),
      signal,
    });
    if (!response.ok) throw new Error(`recommendation request failed: ${response.status}`);
    const payload = (await response.json()) as { cards: ApiRecommendationCard[] };
    return payload.cards.map((card, index) => ({
      recommendationId: card.recommendation_id,
      rank: index + 1,
      restaurantName: card.place_name,
      category: ["한식", "양식", "중식"][index] ?? "추천",
      menuName: card.signature_menu ?? card.menu_name,
      price: card.price ?? 0,
      confidenceScore: Math.round(card.confidence_score),
      distanceM: card.distance_m,
      walkMinutes: card.walk_minutes,
      reasonLine: card.reason_line,
      reasonDetail: card.reason_detail ?? card.reason_line,
      contextTags: card.context_tags,
      address: card.address ?? "주소 확인 중",
    }));
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    return sampleRecommendations;
  }
}

export async function recordMeal(recommendationId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/meals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ member_id: "demo-member", recommendation_id: recommendationId }),
  });
  if (!response.ok) throw new Error("식사 기록을 저장하지 못했습니다.");
}
