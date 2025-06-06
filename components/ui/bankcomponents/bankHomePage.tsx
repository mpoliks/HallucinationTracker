import { ReactElement, useContext } from "react";
import { useFlags, useLDClient } from "launchdarkly-react-client-sdk";
import { motion } from "framer-motion";
import Image from "next/image";
import { Button } from "../button";
import { useRouter } from "next/router";
import { StaticImageData } from "next/image";
import WrapperMain from "../WrapperMain";
import BankNav from "../NavComponent/BankNav";
import LiveLogsContext from "@/utils/contexts/LiveLogsContext";
import { SIGN_UP_STARTED } from "@/components/generators/experimentation-automation/experimentationConstants";

import heroBackgroundCreditcard from "@/public/banking/backgrounds/bank-hero-background-creditcard.svg";
import heroBackgroundDollarSign from "@/public/banking/backgrounds/bank-hero-background-dollarsign.svg";
import checking from "@/public/banking/icons/checking.svg";
import checkingOnHover from "@/public/banking/icons/checking-on-hover.svg";
import creditcard from "@/public/banking/icons/creditcard.svg";
import creditcardOnHover from "@/public/banking/icons/creditcard-on-hover.svg";
import mortgage from "@/public/banking/icons/mortgage.svg";
import mortgageOnHover from "@/public/banking/icons/mortgage-on-hover.svg";
import business from "@/public/banking/icons/business.svg";
import businessOnHover from "@/public/banking/icons/business-on-hover.svg";
import savings from "@/public/banking/icons/savings.svg";
import savingsOnHover from "@/public/banking/icons/savings-on-hover.svg";
import retirementBackground from "@/public/banking/backgrounds/bank-homepage-retirment-card-background.svg";
import specialOfferBackground from "@/public/banking/backgrounds/bank-homepage-specialoffer-background.svg";
import bankHomePageBackgroundRight from "@/public/banking/backgrounds/bank-homepage-background-right.svg";
import bankHomePageBackgroundLeft from "@/public/banking/backgrounds/bank-homepage-background-left.svg";
import { RELEASE_NEW_SIGNUP_PROMO_LDFLAG_KEY } from "@/utils/flagConstants";

export default function BankHomePage() {
	const router = useRouter();
	const ldClient = useLDClient();
	const { logLDMetricSent } = useContext(LiveLogsContext);
	const releaseNewSignUpPromoLDFlag =
		useFlags()[RELEASE_NEW_SIGNUP_PROMO_LDFLAG_KEY] ??
		bankHomePageValues.industryMessages;

	return (
		<>
			<Image
				src={bankHomePageBackgroundRight}
				className="fixed right-0 bottom-0 min-h-screen"
				alt="Bank Home Page Background"
			/>
			<Image
				src={bankHomePageBackgroundLeft}
				className="fixed left-0 bottom-0 min-h-screen"
				alt="Bank Home Page Background"
			/>
			<WrapperMain className="min-w-full">
				<BankNav />
				<header className={`w-full relative 3xl:mx-auto 3xl:max-w-7xl`}>
					<Image
						src={heroBackgroundCreditcard}
						className="absolute right-0 w-2/6 xl:w-2/6 min-w-lg max-w-lg opacity-40 sm:opacity-60 xl:opacity-100 z-[-100]"
						alt="Icon Background"
						priority
						style={{
							maxWidth: "100%",
							width: "auto",
							height: "auto",
						}}
					/>
					<Image
						src={heroBackgroundDollarSign}
						className="absolute left-0 bottom-0 w-2/6 xl:w-2/6 max-w-lg opacity-40 sm:opacity-60 xl:opacity-100 z-[-100]"
						alt="Icon Background"
						priority
						style={{
							maxWidth: "100%",
							width: "auto",
							height: "auto",
						}}
					/>

					<section className="w-full max-w-7xl py-14 sm:py-[8rem] xl:mx-auto flex flex-col sm:flex-row justify-between items-center">
						<div className="flex flex-col text-white w-full sm:w-3/4 xl:w-1/2 justify-start mb-4 pr-0 sm:pr-10 sm:mb-0 gap-y-10 z-10">
							<h1 className="text-5xl sm:text-5xl md:text-6xl lg:text-7xl font-audimat col-span-1 sm:col-span-0 w-full bg-bank-gradient-text-color bg-clip-text text-transparent pr-2 sm:pr-6 md:pr-8 lg:pr-10 xl:pr-8">
								Spend smart with Toggle Bank
							</h1>
							<p className="text-lg sm:text-md md:text-xl lg:text-xl col-span-2 sm:col-span-0 font-sohnelight w-full text-black pr-6 sm:pr-6 md:pr-8 lg:pr-10 xl:pr-8 ">
								{releaseNewSignUpPromoLDFlag
									? "Sign Up for an account today to receieve 50,000 reward points!"
									: bankHomePageValues.industryMessages}
							</p>
							<div className="flex space-x-4 pr-6 sm:pr-2 md:pr-4 lg:pr-6 xl:pr-8">
								<Button
									className="shadow-2xl bg-bank-gradient-blue-background hover:bg-bank-gradient-text-color hover:text-white text-white rounded-3xl font-sohnelight w-28 h-10 sm:w-32 sm:h-11 md:w-36 md:h-12 lg:w-40 lg:h-14 xl:w-36 xl:h-12 text-xs sm:text-md md:text-lg lg:text-xl xl:text-xl"
									onClick={() => {
										ldClient?.track(SIGN_UP_STARTED);
										logLDMetricSent({ metricKey: SIGN_UP_STARTED });
										router.push("/signup");
									}}
								>
									Join Now
								</Button>
								<Button className="shadow-2xl border bg-white hover:bg-bank-gradient-text-color border-blue-800 hover:border-bankhomepagebuttonblue hover:text-white text-blue-800  rounded-3xl font-sohnelight w-28 h-10 sm:w-32 sm:h-11 md:w-36 md:h-12 lg:w-40 lg:h-14 xl:w-36 xl:h-12 text-xs sm:text-md md:text-lg lg:text-xl xl:text-xl">
									Learn More
								</Button>
							</div>
						</div>
					</section>
				</header>
				<section className="2xl:mt-20 mx-auto max-w-7xl">
					<h2 className="flex justify-center text-bankhomepagebuttonblue font-sohne tracking-widest text-md sm:text-xl 2xl:text-2xl">
						EXPLORE SOMETHING NEW
					</h2>

					<section
						className="w-full xl:w-3/4 grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 font-sohnelight text-center  mx-auto gap-y-8 
            xl:gap-y-0 gap-x-8
          sm:gap-x-12 xl:gap-x-24 py-8"
					>
						{bankHomePageValues?.bankingServicesArr.map(
							(ele: { imgSrc: StaticImageData; title: string }, i: number) => {
								return (
									<motion.div
										className="flex flex-col items-center"
										key={i}
										whileHover={{ scale: 1.2 }}
									>
										<div className="relative w-24 h-24  cursor-pointer  bg-white rounded-full shadow-2xl sm:shadow-none flex items-center justify-center">
											<Image
												src={ele?.imgSrc}
												className=""
												alt={ele?.title}
												priority
												style={{
													maxWidth: "100%",
													width: "auto",
													height: "auto",
												}}
											/>
										</div>
										<p className="text-xl mt-2 font-sohnelight">{ele?.title}</p>
									</motion.div>
								);
							}
						)}
					</section>
				</section>
				<section className="w-full xl:w-3/4 mx-auto my-10 max-w-7xl flex flex-col gap-y-10">
					<AdContentRowWrapper
						leftChild={
							<div className="bg-bank-gradient-blue-background p-4 rounded-2xl h-full">
								<AdContentCard
									title={"MORTGAGE"}
									subtitle="Set down new roots"
									contentText="  From finding your new place to getting the keys – we're here to help."
								/>
							</div>
						}
						rightChild={
							<div className="bg-white p-4 rounded-2xl flex h-full">
								<div className="flex flex-col gap-y-6 mt-4 w-full sm:w-1/2">
									<div className="mx-8 text-sm text-gray-400 tracking-widest font-sohnelight">
										RETIREMENT
									</div>
									<div className="mx-8 mt-4 text-blue-600 font-sohne text-xl">
										Prepare for retirement
									</div>
									<div className="text-black mx-8 mb-4 font-sohne text-md">
										Plan for the future by using our Retirement Planning
										Calculator.
									</div>
								</div>
								<div className="w-1/2 items-center justify-center hidden sm:flex">
									<Image
										src={retirementBackground}
										width={200}
										height={50}
										alt="Retirement Background"
										priority
										style={{
											width: "auto",
											maxWidth: "100%",
											height: "auto",
										}}
									/>
								</div>
							</div>
						}
					/>

					{/* Second Row */}
					<AdContentRowWrapper
						xGap={"gap-x-0"}
						yGap="gap-y-0"
						roundedBorderLeftCard="rounded-tl-2xl rounded-tr-2xl sm:rounded-tr-none rounded-bl-none sm:rounded-bl-2xl"
						roundedBorderRightCard="rounded-tr-none sm:rounded-tr-2xl rounded-br-2xl rounded-bl-2xl sm:rounded-bl-none"
						leftChild={
							<div className=" bg-white p-4 rounded-tl-2xl rounded-tr-2xl sm:rounded-tr-none rounded-bl-none sm:rounded-bl-2xl h-full">
								<AdContentCard
									title={"SPECIAL OFFER"}
									titleColor="!text-gray-400"
									subtitle="Take advantage"
									subtitleColor="!text-blue-600"
									contentText="Exclusive credit card offer with premium service from Toggle Bank. Terms apply."
									contentTextColor="!text-black"
								/>
							</div>
						}
						rightChild={
							<Image
								src={specialOfferBackground}
								className="rounded-tr-none sm:rounded-tr-2xl rounded-br-2xl rounded-bl-2xl sm:rounded-bl-none w-full h-[14.5rem] sm:h-full object-cover"
								alt="Retirement Background"
								priority
							/>
						}
					/>
				</section>
			</WrapperMain>
		</>
	);
}

const bankHomePageValues = {
	name: "ToggleBank",
	industryMessages: "More than 100,000 customers worldwide",
	bankingServicesArr: [
		{ imgSrc: checking, title: "Checking" },
		{ imgSrc: business, title: "Business" },
		{ imgSrc: creditcard, title: "Credit Card" },
		{ imgSrc: mortgage, title: "Savings" },
		{ imgSrc: savings, title: "Mortgages" },
	],
	bankingServicesArrOnHover: [
		{ imgSrc: checkingOnHover, title: "Checking" },
		{ imgSrc: businessOnHover, title: "Business" },
		{ imgSrc: creditcardOnHover, title: "Credit Card" },
		{ imgSrc: mortgageOnHover, title: "Savings" },
		{ imgSrc: savingsOnHover, title: "Mortgages" },
	],
};

const AdContentRowWrapper = ({
	leftChild,
	rightChild,
	xGap = "gap-x-8",
	yGap = "gap-y-10 sm:gap-y-0 ",
	roundedBorderLeftCard = "rounded-2xl",
	roundedBorderRightCard = "rounded-2xl",
}: {
	leftChild: ReactElement;
	rightChild: ReactElement;
	xGap?: string;
	yGap?: string;
	roundedBorderLeftCard?: string;
	roundedBorderRightCard?: string;
}) => {
	return (
		<section className={`flex flex-col sm:flex-row ${yGap} ${xGap}`}>
			<div className={`w-full sm:w-1/3 ${roundedBorderLeftCard} shadow-2xl`}>
				{leftChild}
			</div>
			<div className={`w-full sm:w-2/3 ${roundedBorderRightCard} shadow-2xl`}>
				{rightChild}
			</div>
		</section>
	);
};

const AdContentCard = ({
	title,
	titleColor,
	subtitle,
	subtitleColor,
	contentText,
	contentTextColor,
}: {
	title: string;
	titleColor?: string;
	subtitle: string;
	subtitleColor?: string;
	contentText: string;
	contentTextColor?: string;
}) => {
	return (
		<div className="flex flex-col gap-y-6 my-auto h-full justify-center ">
			<div
				className={`mx-8 text-sm text-gray-300 tracking-widest font-sohnelight ${titleColor}`}
			>
				{title}
			</div>
			<div
				className={`mx-8 mt-4 text-white font-sohne text-xl ${subtitleColor}`}
			>
				{subtitle}
			</div>
			<div
				className={`text-gray-300 mx-8 mb-4 font-sohne text-md ${contentTextColor}`}
			>
				{contentText}
			</div>
		</div>
	);
};
