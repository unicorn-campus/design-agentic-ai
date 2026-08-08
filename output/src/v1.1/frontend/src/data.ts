export type Route =
  | "login"
  | "quiz"
  | "location"
  | "dietary"
  | "home"
  | "navigation"
  | "meal"
  | "history"
  | "insights"
  | "profile"
  | "subscription";

export interface Recommendation {
  recommendationId: string;
  rank: number;
  restaurantName: string;
  category: string;
  menuName: string;
  price: number;
  confidenceScore: number;
  distanceM: number;
  walkMinutes: number;
  reasonLine: string;
  reasonDetail: string;
  contextTags: string[];
  address: string;
}

export type MealFeedback = "good" | "bad" | "neutral";

export interface MealHistoryEntry {
  recommendationId?: string;
  day: number;
  restaurant: string;
  category: string;
  feedback: MealFeedback;
}

export const foods = [
  { name: "김치찌개", emoji: "🍲", tags: "#한식 #국물 #매운맛" },
  { name: "크림 파스타", emoji: "🍝", tags: "#양식 #면 #크리미" },
  { name: "초밥", emoji: "🍣", tags: "#일식 #생선 #담백" },
  { name: "짜장면", emoji: "🍜", tags: "#중식 #면 #달콤" },
  { name: "샐러드", emoji: "🥗", tags: "#건강식 #가벼운 #채소" },
];

export const allergens = ["땅콩", "갑각류", "우유", "밀", "달걀", "대두", "생선", "조개류"];
export const dietTypes = ["일반", "채식", "비건", "할랄", "기타"];
export const rejectReasons = ["오늘 기분 아님", "너무 멀어요", "최근에 갔어요", "기타"];

export const sampleRecommendations: Recommendation[] = [
  {
    recommendationId: "rec-001",
    rank: 1,
    restaurantName: "미소된장",
    category: "한식",
    menuName: "된장찌개 정식",
    price: 8500,
    confidenceScore: 87,
    distanceM: 350,
    walkMinutes: 5,
    reasonLine: "비 오는 날 따뜻한 국물 추천",
    reasonDetail: "비 오는 날이고 어제 양식을 드셨으니 따뜻한 한식 국물을 추천했어요.",
    contextTags: ["🌧️ 날씨", "📋 어제 이력", "❤️ 취향"],
    address: "서울 강남구 테헤란로 123",
  },
  {
    recommendationId: "rec-002",
    rank: 2,
    restaurantName: "봉주르 파스타",
    category: "양식",
    menuName: "크림 파스타",
    price: 11000,
    confidenceScore: 72,
    distanceM: 550,
    walkMinutes: 8,
    reasonLine: "이번 주 한식이 많았으니 양식",
    reasonDetail: "이번 주 식사 이력을 반영해 기분 전환이 되는 양식을 추천했어요.",
    contextTags: ["📋 이번 주 이력", "❤️ 취향"],
    address: "서울 강남구 역삼로 45",
  },
  {
    recommendationId: "rec-003",
    rank: 3,
    restaurantName: "홍콩반점",
    category: "중식",
    menuName: "짬뽕",
    price: 9000,
    confidenceScore: 65,
    distanceM: 200,
    walkMinutes: 3,
    reasonLine: "가까운 곳에서 빠르게",
    reasonDetail: "남은 점심시간을 고려해 가까운 곳을 우선했어요.",
    contextTags: ["⏰ 시간", "📍 거리"],
    address: "서울 강남구 테헤란로 88",
  },
];

export const mealHistory: MealHistoryEntry[] = [
  { day: 1, restaurant: "미소된장", category: "한식", feedback: "good" },
  { day: 3, restaurant: "봉주르 파스타", category: "양식", feedback: "good" },
  { day: 4, restaurant: "홍콩반점", category: "중식", feedback: "bad" },
  { day: 7, restaurant: "스시히로", category: "일식", feedback: "good" },
  { day: 12, restaurant: "미소된장", category: "한식", feedback: "good" },
  { day: 17, restaurant: "미소된장", category: "한식", feedback: "good" },
];
