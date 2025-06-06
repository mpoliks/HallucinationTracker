import "@/styles/globals.css";
import type { AppProps } from "next/app";
import NoSSRWrapper from "@/components/no-ssr";
import dynamic from "next/dynamic";
import { LoginProvider } from "@/utils/contexts/login";
import Head from "next/head";
import { QuickCommandDialog } from "@/components/generators/experimentation-automation/quickcommand";
import { LiveLogsProvider } from "@/utils/contexts/LiveLogsContext";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/ui/app-sidebar";
import { SignupProvider } from "@/components/SignUpProvider";
let c;

if (typeof window !== "undefined") {
  const ContextProvider = dynamic(() => import("@/components/ContextProvider"), {
    ssr: false,
  });

  const TelemetryProvider = dynamic(() => import("@/components/TelemetryProvider"), {
    ssr: false,
  });

  c = ({ Component, pageProps }: AppProps) => {
    return (
      <NoSSRWrapper>
        <ContextProvider>
          <TelemetryProvider>
            <LoginProvider>
              <LiveLogsProvider>
                <SidebarProvider
                  defaultOpen={false}
                  style={{
                    "--sidebar-width": "30vw",
                    "--sidebar-width-mobile": "100vw",
                  }}
                >
                  <SignupProvider>
                    <QuickCommandDialog>
                      <Head>
                        <meta
                          name="viewport"
                          content="width=device-width, initial-scale=1.0, maximum-scale=1.0,user-scalable=0"
                        />
                        <link rel="apple-touch-icon" href="/apple-icon.png" />
                      </Head>
                      <Component {...pageProps} />
                      <AppSidebar />
                      <SidebarTrigger
                        className="bg-airlinedarkblue fixed bottom-4 left-4 h-12 w-12 hover:bg-airlinedarkblue z-10"
                        title="Click to open sidebar to show server side calls"
                      />
                    </QuickCommandDialog>
                  </SignupProvider>
                </SidebarProvider>
              </LiveLogsProvider>
            </LoginProvider>
          </TelemetryProvider>
        </ContextProvider>
      </NoSSRWrapper>
    );
  };
} else {
  c = () => null;
}

export default c;
