import { ElementType, useEffect, useState } from "react";
import { asyncWithLDProvider } from "launchdarkly-react-client-sdk";
import { setCookie } from "cookies-next";
import { LD_CONTEXT_COOKIE_KEY } from "@/utils/constants";
import { LDContextInterface } from "@/utils/typescriptTypesInterfaceLogin";
import { SyncLoader } from "react-spinners";
import { MultiKindLDContext } from "@/utils/MultiKindLDContext";
import { getLocation, getDeviceForContext } from "@/utils/utils";
import { v4 as uuidv4 } from "uuid";

const ContextProvider = ({ children }: { children: React.ReactNode }) => {
    const [LDProviderComponent, setLDProviderComponent] = useState<ElementType>();

    useEffect(() => {
        const initializeLDProvider = async () => {
            const context: LDContextInterface = MultiKindLDContext({
                isAnonymous: true,
                audienceKey: uuidv4().slice(0, 10),
                userRole: "",
                userTier: "",
                userName: "",
                userEmail: "",
                userKey: uuidv4().slice(0, 10),
                newDevice: getDeviceForContext(),
                newLocation: getLocation(),
            });

            setCookie(LD_CONTEXT_COOKIE_KEY, context);

            const FetchedProvider = await asyncWithLDProvider({
                clientSideID: process.env.NEXT_PUBLIC_LD_CLIENT_KEY || "",
                reactOptions: {
                    useCamelCaseFlagKeys: false,
                },
                options: {
                    application: {
                        id: "togglebank",
                    },
                    eventCapacity: 500,
                    privateAttributes: ["email", "name"],
                },
                context: context,
            });

            setLDProviderComponent(() => FetchedProvider);
        };

        initializeLDProvider();
    }, []);

    if (!LDProviderComponent) {
        return <LoadingComponent />;
    }

    return <LDProviderComponent>{children}</LDProviderComponent>;
};

export default ContextProvider;

const LoadingComponent = () => {
    return (
        <div className="w-[100vw] h-[100vh] flex items-center justify-center">
            <div className="flex flex-col gap-y-8 items-center px-4">
                <h1 className="text-4xl text-center">Loading LaunchDarkly...</h1>
                <SyncLoader
                    className=""
                    size={30}
                    margin={20}
                    speedMultiplier={0.8}
                    color={"#405BFF"}
                />
            </div>
        </div>
    );
};
