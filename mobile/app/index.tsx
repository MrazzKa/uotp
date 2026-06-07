import { Redirect } from "expo-router";
import { useEffect, useState } from "react";

import { loadTokens, useAuthStore } from "../src/store/auth";

export default function Index() {
  const [ready, setReady] = useState(false);
  const accessToken = useAuthStore((state) => state.accessToken);

  useEffect(() => {
    loadTokens().finally(() => setReady(true));
  }, []);

  if (!ready) {
    return null;
  }

  return <Redirect href={accessToken ? "/home" : "/login"} />;
}
