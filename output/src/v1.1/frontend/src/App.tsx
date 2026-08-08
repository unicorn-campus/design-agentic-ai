import { useEffect, useState } from "react";
import { sampleRecommendations, type Recommendation, type Route } from "./data";
import { DietaryScreen, LocationScreen, LoginScreen, QuizScreen } from "./screens/OnboardingScreens";
import { HomeScreen, InsightsScreen, MealScreen, NavigationScreen, ProfileScreen, SubscriptionScreen } from "./screens/MainScreens";

const routes: Route[] = ["login", "quiz", "location", "dietary", "home", "navigation", "meal", "insights", "profile", "subscription"];

function routeFromHash(): Route {
  const value = window.location.hash.replace("#", "") as Route;
  return routes.includes(value) ? value : "login";
}

export function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [recommendation, setRecommendation] = useState<Recommendation>(sampleRecommendations[0]);
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

  switch (route) {
    case "login": return <LoginScreen navigate={navigate} />;
    case "quiz": return <QuizScreen navigate={navigate} />;
    case "location": return <LocationScreen navigate={navigate} />;
    case "dietary": return <DietaryScreen navigate={navigate} />;
    case "home": return <HomeScreen navigate={navigate} selectRecommendation={setRecommendation} />;
    case "navigation": return <NavigationScreen navigate={navigate} recommendation={recommendation} />;
    case "meal": return <MealScreen navigate={navigate} recommendation={recommendation} />;
    case "insights": return <InsightsScreen navigate={navigate} />;
    case "profile": return <ProfileScreen navigate={navigate} />;
    case "subscription": return <SubscriptionScreen navigate={navigate} />;
  }
}
