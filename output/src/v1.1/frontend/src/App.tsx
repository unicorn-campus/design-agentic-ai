import { useEffect, useState } from "react";
import { mealHistory, sampleRecommendations, type MealFeedback, type MealHistoryEntry, type Recommendation, type Route } from "./data";
import { DietaryScreen, LocationScreen, LoginScreen, QuizScreen } from "./screens/OnboardingScreens";
import { HomeScreen, InsightsScreen, MealScreen, NavigationScreen, ProfileScreen, SubscriptionScreen } from "./screens/MainScreens";

const routes: Route[] = ["login", "quiz", "location", "dietary", "home", "navigation", "meal", "history", "insights", "profile", "subscription"];

function routeFromHash(): Route {
  const value = window.location.hash.replace("#", "") as Route;
  return routes.includes(value) ? value : "login";
}

export function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [recommendation, setRecommendation] = useState<Recommendation>(sampleRecommendations[0]);
  const [locationEnabled, setLocationEnabled] = useState(false);
  const [dietaryConfigured, setDietaryConfigured] = useState(false);
  const [mealRecords, setMealRecords] = useState<MealHistoryEntry[]>(mealHistory);
  useEffect(() => {
    const onHashChange = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (next: Route) => {
    window.location.hash = next;
    setRoute(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const addMealRecord = (feedback: MealFeedback) => {
    const entry: MealHistoryEntry = {
      recommendationId: recommendation.recommendationId,
      day: new Date().getDate(),
      restaurant: recommendation.restaurantName,
      category: recommendation.category,
      feedback,
    };
    setMealRecords((current) => [
      ...current.filter((item) => item.recommendationId !== entry.recommendationId || item.day !== entry.day),
      entry,
    ]);
  };

  switch (route) {
    case "login": return <LoginScreen navigate={navigate} />;
    case "quiz": return <QuizScreen navigate={navigate} />;
    case "location": return <LocationScreen navigate={navigate} onLocationChoice={setLocationEnabled} />;
    case "dietary": return <DietaryScreen navigate={navigate} onConfigured={setDietaryConfigured} />;
    case "home": return <HomeScreen navigate={navigate} selectRecommendation={setRecommendation} />;
    case "navigation": return <NavigationScreen navigate={navigate} recommendation={recommendation} />;
    case "meal": return <MealScreen navigate={navigate} recommendation={recommendation} onMealCompleted={addMealRecord} />;
    case "history": return <InsightsScreen navigate={navigate} view="history" records={mealRecords} />;
    case "insights": return <InsightsScreen navigate={navigate} view="insight" records={mealRecords} />;
    case "profile": return <ProfileScreen navigate={navigate} dietaryConfigured={dietaryConfigured} locationEnabled={locationEnabled} onLocationChange={setLocationEnabled} />;
    case "subscription": return <SubscriptionScreen navigate={navigate} />;
  }
}
