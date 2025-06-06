import { useEffect, useState, useRef, useContext, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardHeader,
	CardContent,
	CardFooter,
} from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import LoginContext from "@/utils/contexts/login";
import { v4 as uuidv4 } from "uuid";
import { useLDClient, useFlags } from "launchdarkly-react-client-sdk";
import { PulseLoader } from "react-spinners";
import { useToast } from "@/components/ui/use-toast";
import { BatteryCharging } from "lucide-react";
import {
	PERSONA_ROLE_DEVELOPER,
	COHERE,
	ANTHROPIC,
	DEFAULT_AI_MODEL,
	ANTHROPIC_CLAUDE,
	COHERE_CORAL,
} from "@/utils/constants";
import LiveLogsContext from "@/utils/contexts/LiveLogsContext";
import { useIsMobile } from "../hooks/use-mobile";
import { Sheet, SheetContent, SheetClose } from "@/components/ui/sheet";
import {
	AIModelInterface,
	ChatBotMessageInterface,
	ChatBotAIApiResponseInterface,
	UserChatInputResponseInterface,
} from "@/utils/typescriptTypesInterfaceIndustry";
import { useSidebar } from "../ui/sidebar";
import { cn } from "@/utils/utils";
import { motion } from "framer-motion";
import { AI_CHATBOT_BAD_SERVICE,AI_CHATBOT_GOOD_SERVICE } from "../generators/experimentation-automation/experimentationConstants";
import { AI_CONFIG_TOGGLEBOT_LDFLAG_KEY } from "@/utils/flagConstants";

function ChatBotInterface({
	cardRef,
	isOpen,
	toggleSidebar,
}: {
	cardRef: React.RefObject<HTMLDivElement>;
	isOpen: boolean;
	toggleSidebar: (boolean?: boolean) => void;
}) {
	const ldClient = useLDClient();
	const aiNewModelChatbotFlag: AIModelInterface =
		useFlags()[AI_CONFIG_TOGGLEBOT_LDFLAG_KEY] ?? DEFAULT_AI_MODEL;
	const aiConfigKey = AI_CONFIG_TOGGLEBOT_LDFLAG_KEY;
	const { open } = useSidebar();

	const [messages, setMessages] = useState<ChatBotMessageInterface[]>([]);
	const [userInput, setUserInput] = useState("");
	const [actualModelName, setActualModelName] = useState<string | null>(null);
	const [lastMetrics, setLastMetrics] = useState<ChatBotAIApiResponseInterface['metrics'] | null>(null);
	const [showMetrics, setShowMetrics] = useState(false);

	const submitChatBotQuery = async () => {
		if (!userInput.trim()) return; // Do not send empty messages

		const currentInput = userInput; // Capture the current input
		setIsLoading(true);
		setUserInput(""); // Clear the input field immediately

		// Display the user's message right away
		const userMessage: ChatBotMessageInterface = {
			role: "user",
			content: currentInput,
			id: uuidv4().slice(0, 4),
		};

		const loadingMessage: ChatBotMessageInterface = {
			role: "system",
			content: "loading",
			id: uuidv4().slice(0, 4),
		};
		
		setMessages(prevMessages => [...prevMessages, userMessage, loadingMessage]);

		try {
			const userInputRes: UserChatInputResponseInterface = {
				aiConfigKey: aiConfigKey,
				userInput: currentInput, // Use the captured input
			};
	
			const response = await fetch("/api/chat", {
				method: "POST",
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(userInputRes),
			});
	
			if (!response.ok) {
				// Handle HTTP errors
				const errorData = await response.json().catch(() => ({ error: 'Failed to parse error response' }));
				throw new Error(errorData.error || `Request failed with status ${response.status}`);
			}
	
			const data: ChatBotAIApiResponseInterface = await response.json();
	
			applyChatBotNewMessage(data);
		} catch (error) {
			console.error("Chat query failed:", error);
			const errorMessage: ChatBotMessageInterface = {
				role: "assistant",
				content: error instanceof Error ? error.message : "An unexpected error occurred.",
				id: uuidv4().slice(0, 4),
			};
			setMessages(prevMessages => 
				prevMessages.filter(m => m.content !== 'loading').concat(errorMessage)
			);
		} finally {
			setIsLoading(false);
		}
	};

	const sendChatbotFeedback = async (feedback: string) => {
		const response = await fetch("/api/chatbotfeedback", {
			method: "POST",
			body: JSON.stringify({
				feedback,
				aiConfigKey,
			}),
		});
		return await response.json();
	};

	// BELOW IS CODE NOT RELATED TO AI CONFIG

	const applyUserNewMessage = () => {
		setUserInput("");

		const userMessage: ChatBotMessageInterface = {
			role: "user",
			content: userInput,
			id: uuidv4().slice(0, 4),
		};

		const loadingMessage: ChatBotMessageInterface = {
			role: "system",
			content: "loading",
			id: uuidv4().slice(0, 4),
		};

		setMessages([...messages, userMessage, loadingMessage]);
	};

	const applyChatBotNewMessage = (
		chatBotResponse: ChatBotAIApiResponseInterface
	) => {
		// Update the actual model name from the API response
		if (chatBotResponse.modelName) {
			setActualModelName(chatBotResponse.modelName);
		}

		// Store metrics from the API response
		if (chatBotResponse.metrics) {
			console.log("Frontend: Received metrics:", chatBotResponse.metrics);
			setLastMetrics(chatBotResponse.metrics);
		} else {
			console.log("Frontend: No metrics in response:", chatBotResponse);
		}

		let aiAnswer: string =
			chatBotResponse.response || "I'm sorry. Please try again.";

		let assistantMessage: ChatBotMessageInterface = {
			role: "assistant",
			content: aiAnswer,
			id: uuidv4().slice(0, 4),
		};

		setMessages((prevMessages) =>
			prevMessages
				.filter((msg) => msg.content !== "loading")
				.concat(assistantMessage)
		);
	};

	const surveyResponseNotification = (surveyResponse: string) => {
		ldClient?.track(surveyResponse, ldClient.getContext());

		sendChatbotFeedback(surveyResponse);
		logLDMetricSent({ metricKey: surveyResponse });
		ldClient?.flush();
		toast({
			title: `Thank you for your response!`,
			wrapperStyle: "bg-green-600 text-white font-sohne text-base border-none",
		});
	};

	const [isLoading, setIsLoading] = useState(false);
	const [chatHeaderHeight, setChatHeaderHeight] = useState(0);
	const [chatFooterHeight, setChatFooterHeight] = useState(0);
	const isMobile = useIsMobile();
	const { toast } = useToast();
	const { userObject } = useContext(LoginContext);
	const { logLDMetricSent } = useContext(LiveLogsContext);
	const chatContentRef = useRef<HTMLDivElement>(null);
	const chatHeaderRef = useRef<HTMLDivElement>(null);
	const chatFooterRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (chatContentRef.current) {
			chatContentRef.current.scrollTop = chatContentRef.current.scrollHeight;
		}
	}, [messages]);

	useEffect(() => {
		if (chatHeaderRef.current?.offsetHeight) {
			setChatHeaderHeight(chatHeaderRef?.current?.offsetHeight);
		}
	}, [chatHeaderHeight]);

	useEffect(() => {
		if (chatFooterRef.current?.offsetHeight) {
			setChatFooterHeight(chatFooterRef?.current?.offsetHeight);
		}
	}, [chatFooterHeight]);

	const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setUserInput(e.target.value);
	};

	const aiModelName = () => {
		// Prioritize actual model name from API response
		if (actualModelName) {
			// Format the model name for display with specific variants
			if (actualModelName.includes("nova")) {
				return "Amazon Nova Pro";
			} else if (actualModelName.includes("claude")) {
				// Be specific about Claude variants
				if (actualModelName.includes("haiku")) {
					return "Claude Haiku";
				} else if (actualModelName.includes("sonnet")) {
					return "Claude Sonnet";
				} else if (actualModelName.includes("instant")) {
					return "Claude Instant";
				} else if (actualModelName.includes("opus")) {
					return "Claude Opus";
				} else {
					return "Anthropic Claude";
				}
			} else if (actualModelName.includes("cohere")) {
				return "Cohere Coral";
			} else if (actualModelName.includes("titan")) {
				return "Amazon Titan";
			} else {
				// For any other model, show a cleaned up version of the actual model name
				return actualModelName.replace(/^(us\.|amazon\.|anthropic\.)/, "").replace(/-v?\d+:?\d*$/, "");
			}
		}
		
		// Default to AI Assistant until we get actual model name from API
		return "AI Assistant";
	};

	return (
		<>
			{isOpen && (
				<div
					ref={cardRef}
					className={cn(
						"relative lg:fixed lg:bottom-16 lg:right-0 lg:z-50 flex items-end justify-end p-0 lg:p-6 max-w-full",
						open && "right-0 lg:right-[30vw]"
					)}
				>
					<Card className="w-full lg:max-w-md lg:mx-auto">
						<CardHeader
							className="flex flex-row items-center"
							ref={chatHeaderRef}
						>
							<div className="flex items-center space-x-4">
								<Avatar>
									<img
										src={"/personas/ToggleAvatar.png"}
										alt="Chatbot Avatar"
									/>{" "}
									<AvatarFallback>CB</AvatarFallback>
								</Avatar>
								<div>
									<p className="text-sm font-medium leading-none">
										Chatbot Assistant
									</p>
									{aiNewModelChatbotFlag?.model?.name && (
										<>
											<p className={"text-sm text-gray-500 dark:text-gray-400"}>
												Powered by{" "}
												<span
													className={`font-bold text-white ${
														(actualModelName?.includes("cohere") || aiNewModelChatbotFlag?.model?.name?.includes("cohere"))
															? "!text-cohereColor"
															: ""
													} ${
														(actualModelName?.includes("claude") || aiNewModelChatbotFlag?.model?.name?.includes("claude"))
															? "!text-anthropicColor"
															: ""
													} ${
														(actualModelName?.includes("nova") || aiNewModelChatbotFlag?.model?.name?.includes("nova"))
															? "!text-amazonColor"
															: ""
													} ${
														(actualModelName?.includes("titan") || aiNewModelChatbotFlag?.model?.name?.includes("titan"))
															? "!text-amazonColor"
															: ""
													}
                      `}
												>
													{aiModelName()}
												</span>{" "}
												with{" "}
												<span className="text-amazonColor font-bold">
													{" "}
													Amazon Bedrock{" "}
												</span>
											</p>{" "}
										</>
									)}
								</div>
							</div>
							<div className="ml-auto flex items-center space-x-2">
								<Button
									variant="ghost"
									size="icon"
									title="How was our service today?"
									className="rounded-full bg-[#55efc4] text-gray-900 hover:bg-[#00b894] dark:bg-[#55efc4] dark:text-gray-900 dark:hover:bg-[#00b894]"
									onClick={() => {
										surveyResponseNotification(AI_CHATBOT_GOOD_SERVICE);
									}}
								>
									<SmileIcon className="h-6 w-6" />
									<span className="sr-only">Good</span>
								</Button>
								<Button
									variant="ghost"
									size="icon"
									title="How was our service today?"
									className="rounded-full bg-[#ff7675] text-gray-50 hover:bg-[#d63031] dark:bg-[#ff7675] dark:text-gray-50 dark:hover:bg-[#d63031]"
									onClick={() => {
										surveyResponseNotification(AI_CHATBOT_BAD_SERVICE);
									}}
								>
									<FrownIcon className="h-6 w-6" />
									<span className="sr-only">Bad</span>
								</Button>
								<Button
									variant="ghost"
									size="icon"
									className="ml-auto rounded-full hidden lg:block"
									onClick={() => toggleSidebar(false)}
								>
									<XIcon className="h-6 w-6" />
									<span className="sr-only">Close Chatbot</span>
								</Button>
							</div>
						</CardHeader>
						<CardContent
							className={`lg:h-[500px] overflow-y-auto`}
							ref={chatContentRef}
							style={
								isMobile
									? {
											height: `calc(100vh - ${
												chatHeaderHeight + chatFooterHeight + 40
											}px)`,
									  }
									: {}
							}
						>
							{aiNewModelChatbotFlag?._ldMeta?.enabled && (
								<div className="space-y-4">
									<div className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800">
										Hello! How can I assist you today?
									</div>
									{messages.map((m) => {
										if (m?.role === "assistant") {
											return (
												<div
													key={m?.id}
													className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800"
												>
													{m?.content}
												</div>
											);
										}

										if (
											m?.role === "system" &&
											m?.content === "loading" &&
											isLoading
										) {
											return (
												<div
													key={m?.id}
													className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800"
												>
													<PulseLoader className="" />
												</div>
											);
										}

										return (
											<div
												key={m?.id}
												className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm ml-auto bg-gradient-airways text-white dark:bg-gray-50 dark:text-gray-900"
											>
												{m?.content}
											</div>
										);
									})}

									{/* Metrics Display */}
									{aiNewModelChatbotFlag?._ldMeta?.enabled && lastMetrics && (
										<div className="mt-4 border-t pt-2">
											<Button
												variant="ghost"
												size="sm"
												onClick={() => setShowMetrics(!showMetrics)}
												className="text-xs text-gray-500 hover:text-gray-700 p-1 h-auto"
											>
												{showMetrics ? '▼' : '▶'} Response Metrics
											</Button>
											{showMetrics && (
												<div className="mt-2 text-xs text-gray-600 bg-gray-50 dark:bg-gray-800 rounded p-3 space-y-1">
													{lastMetrics.grounding_score !== undefined && (
														<div className="flex justify-between">
															<span>Grounding Score:</span>
															<span className={lastMetrics.grounding_score >= (lastMetrics.grounding_threshold || 0.8) ? 'text-green-600' : 'text-orange-600'}>
																{(lastMetrics.grounding_score * 100).toFixed(1)}% (threshold: {((lastMetrics.grounding_threshold || 0) * 100).toFixed(1)}%)
															</span>
														</div>
													)}
													{lastMetrics.relevance_score !== undefined && (
														<div className="flex justify-between">
															<span>Relevance Score:</span>
															<span className={lastMetrics.relevance_score >= (lastMetrics.relevance_threshold || 0.7) ? 'text-green-600' : 'text-orange-600'}>
																{(lastMetrics.relevance_score * 100).toFixed(1)}% (threshold: {((lastMetrics.relevance_threshold || 0) * 100).toFixed(1)}%)
															</span>
														</div>
													)}
													{lastMetrics.factual_accuracy !== undefined && (
														<div className="flex justify-between">
															<span>Factual Accuracy:</span>
															<span className={lastMetrics.factual_accuracy >= 0.8 ? 'text-green-600' : 'text-orange-600'}>
																{(lastMetrics.factual_accuracy * 100).toFixed(1)}%
															</span>
														</div>
													)}
													{lastMetrics.processing_latency_ms !== undefined && (
														<div className="flex justify-between">
															<span>Processing Latency:</span>
															<span>{lastMetrics.processing_latency_ms}ms</span>
														</div>
													)}
													{lastMetrics.contextual_grounding_units !== undefined && (
														<div className="flex justify-between">
															<span>Grounding Units Used:</span>
															<span>{lastMetrics.contextual_grounding_units}</span>
														</div>
													)}
													{lastMetrics.characters_guarded !== undefined && lastMetrics.total_characters !== undefined && (
														<div className="flex justify-between">
															<span>Characters Guarded:</span>
															<span>{lastMetrics.characters_guarded}/{lastMetrics.total_characters}</span>
														</div>
													)}
													{lastMetrics.knowledge_base_id && (
														<div className="flex justify-between">
															<span>Knowledge Base:</span>
															<span className="font-mono text-xs">{lastMetrics.knowledge_base_id}</span>
														</div>
													)}
													{lastMetrics.guardrail_id && (
														<div className="flex justify-between">
															<span>Guardrail:</span>
															<span className="font-mono text-xs">{lastMetrics.guardrail_id}</span>
														</div>
													)}
												</div>
											)}
										</div>
									)}
								</div>
							)}
						</CardContent>
						<CardFooter className="p-4 lg:p-6" ref={chatFooterRef}>
							<form
								className="flex w-full items-center space-x-2"
							>
								<Input
									placeholder="Type your message..."
									className="pr-12"
									value={userInput}
									onChange={handleInputChange}
									onKeyDown={(e) => {
										if (e.key === "Enter") {
											submitChatBotQuery();
										}
									}}
									disabled={isLoading}
								/>
								<Button
									type="submit"
									className="absolute right-2 top-1/2 -translate-y-1/2"
									size="icon"
									onClick={submitChatBotQuery}
									disabled={isLoading}
								>
									<SendIcon className="h-5 w-5" />
								</Button>
							</form>
						</CardFooter>
					</Card>
				</div>
			)}
		</>
	);
}

export default function Chatbot() {
	const aiNewModelChatbotFlag: AIModelInterface =
		useFlags()[AI_CONFIG_TOGGLEBOT_LDFLAG_KEY] == undefined
			? DEFAULT_AI_MODEL
			: useFlags()[AI_CONFIG_TOGGLEBOT_LDFLAG_KEY];

	const isMobile = useIsMobile();
	const [isOpen, setIsOpen] = useState(false);
	const [openMobile, setOpenMobile] = useState(false);
	const cardRef = useRef<HTMLDivElement>(null);
	const { open } = useSidebar();

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (cardRef.current && !cardRef.current.contains(event.target as Node)) {
				toggleSidebar(false);
			}
		};

		if (isOpen) {
			document.addEventListener("mousedown", handleClickOutside);
		} else {
			document.removeEventListener("mousedown", handleClickOutside);
		}

		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, [isOpen]);

	const toggleSidebar = useCallback(
		(boolean?: boolean) => {
			if (boolean === false) {
				return isMobile ? setOpenMobile(false) : setIsOpen(false);
			}
			return isMobile
				? setOpenMobile((open) => !open)
				: setIsOpen((open) => !open);
		},
		[isMobile, setIsOpen, setOpenMobile]
	);

	return (
		<>
			<motion.div
				initial={{ opacity: 0 }}
				animate={{ opacity: 1 }}
				transition={{ duration: 1.5 }}
				className={cn(
					"fixed bottom-4 right-4 z-10",
					open && "lg:right-[calc(30vw+1rem)]"
				)}
			>
				<Button
					variant="ghost"
					size="icon"
					className="bg-airlinedarkblue text-gray-50 hover:bg-airlinedarkblue/90 dark:bg-gray-50 dark:text-gray-900 dark:hover:bg-gray-50/90 shadow-lg !h-12 !w-12 animate-pulse hover:animate-none"
					onClick={() => toggleSidebar()}
				>
					{isOpen && <XIcon className="h-8 w-8" />}
					{!isOpen && aiNewModelChatbotFlag?._ldMeta?.enabled !== false && (
						<MessageCircleIcon className="h-8 w-8" />
					)}
					{!isOpen && aiNewModelChatbotFlag?._ldMeta?.enabled === false && (
						<BatteryCharging className="h-8 w-8" />
					)}
					<span className="sr-only">Open Chatbot</span>
				</Button>
			</motion.div>
			{isMobile ? (
				<Sheet open={openMobile} onOpenChange={setOpenMobile}>
					<SheetContent
						data-sidebar="sidebar"
						data-mobile="true"
						className="w-full h-full bg-sidebar p-0 text-sidebar-foreground !border-0 [&>button]:hidden"
						side={"right"}
						id="sidebar-mobile"
					>
						<div className="flex h-full w-full flex-col ">
							<ChatBotInterface
								cardRef={cardRef}
								isOpen={openMobile}
								toggleSidebar={toggleSidebar}
							/>
							<SheetClose className="h-10 w-full bg-airlinedarkblue text-white">
								Close
							</SheetClose>
						</div>
					</SheetContent>
				</Sheet>
			) : (
				<ChatBotInterface
					cardRef={cardRef}
					isOpen={isOpen}
					toggleSidebar={toggleSidebar}
				/>
			)}
		</>
	);
}

function MessageCircleIcon(props: any) {
	return (
		<svg
			{...props}
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
		</svg>
	);
}

function SendIcon(props: any) {
	return (
		<svg
			{...props}
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			<path d="m22 2-7 20-4-9-9-4Z" />
			<path d="M22 2 11 13" />
		</svg>
	);
}

function XIcon(props: any) {
	return (
		<svg
			{...props}
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			<path d="M18 6 6 18" />
			<path d="m6 6 12 12" />
		</svg>
	);
}

function SmileIcon(props: any) {
	return (
		<svg
			{...props}
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			<circle cx="12" cy="12" r="10" />
			<path d="M8 14s1.5 2 4 2 4-2 4-2" />
			<line x1="9" x2="9.01" y1="9" y2="9" />
			<line x1="15" x2="15.01" y1="9" y2="9" />
		</svg>
	);
}

function FrownIcon(props: any) {
	return (
		<svg
			{...props}
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			<circle cx="12" cy="12" r="10" />
			<path d="M16 16s-1.5-2-4-2-4 2-4 2" />
			<line x1="9" x2="9.01" y1="9" y2="9" />
			<line x1="15" x2="15.01" y1="9" y2="9" />
		</svg>
	);
}
