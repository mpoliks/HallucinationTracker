import { useContext } from "react";
import LoginContext from "@/utils/contexts/login";
import BankHomePage from "@/components/ui/bankcomponents/bankHomePage";
import Chatbot from "@/components/chatbot/ChatBot";
import BankUserDashboard from "@/components/ui/bankcomponents/bankUserDashboard";

export default function Bank() {
    const { isLoggedIn } = useContext(LoginContext);
    return (
        <main className={` w-full min-h-screen  bg-cover bg-center bg-no-repeat pb-10`}>
            {!isLoggedIn ? <BankHomePage /> : <BankUserDashboard />}
            <Chatbot />
        </main>
    );
}
