// LucidOrbBot - Opening Range Breakout for NQ / MNQ with LucidFlex 50K rule guards.
// NinjaTrader 8 strategy. Put this file in:
//   Documents\NinjaTrader 8\bin\Custom\Strategies\LucidOrbBot.cs
// then NinjaScript Editor -> F5 (compile).
//
// Chart: MNQ (or NQ) 1 Minute. Set NinjaTrader's time zone to Eastern Time
// (Tools > Options > General > Time zone) so the session times below are ET.
//
// Two presets (Mode):
//   Sprint - one trade per day, small target / wide stop, sized so 3 winning days
//            pass the evaluation. Highest chance of passing in 3 days, but ONE
//            losing trade usually ends the account.
//   Steady - two trades per day max, 1:2 risk/reward, small daily caps.
//            Takes ~2-4 weeks, best chance of passing AND getting paid if the
//            strategy has a real edge.
//
// Nothing here guarantees profit. Run it in Sim / Strategy Analyzer first.

#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public enum LucidBotMode { Sprint, Steady }

    public class LucidOrbBot : Strategy
    {
        private double orHigh, orLow;
        private bool orReady;
        private int tradesToday;
        private double dayStartCumProfit;
        private bool doneForDay;
        private bool tradedLong, tradedShort;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "LucidOrbBot";
                Description = "Opening Range Breakout with LucidFlex rule guards (daily caps, drawdown room, consistency).";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 60;
                BarsRequiredToTrade = 20;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TraceOrders = false;

                Mode = LucidBotMode.Steady;
                OrStart = 93000;
                OrEnd = 94500;
                LastEntryTime = 113000;
                FlattenTime = 155000;
                MinStopPoints = 15;
                MaxStopPoints = 60;
                RiskDollars = 250;
                RewardRisk = 2.0;
                MaxTradesPerDay = 2;
                DailyProfitCap = 500;
                DailyLossStop = 500;
                MaxContracts = 40;
                ProfitTarget = 3000;
                ProfitSoFar = 0;
                DrawdownFloor = 48000;
                FloorBuffer = 75;
                UseAccountBalance = true;
            }
            else if (State == State.Configure)
            {
                if (Mode == LucidBotMode.Sprint)
                {
                    // one shot per day: risk ~ $1,900 to make ~ $1,050 (needs DLL OFF on the account)
                    RewardRisk = 0.55;
                    RiskDollars = 1900;
                    MaxTradesPerDay = 1;
                    DailyProfitCap = 1000;
                    DailyLossStop = 1900;
                }
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            if (Bars.IsFirstBarOfSession)
                ResetDay();

            int t = ToTime(Time[0]);

            // 1) build the opening range
            if (t > OrStart && t <= OrEnd)
            {
                orHigh = orReady ? Math.Max(orHigh, High[0]) : High[0];
                orLow = orReady ? Math.Min(orLow, Low[0]) : Low[0];
                orReady = true;
                return;
            }

            // 2) flatten before the close
            if (t >= FlattenTime)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong();
                if (Position.MarketPosition == MarketPosition.Short) ExitShort();
                doneForDay = true;
                return;
            }

            // 3) daily guards
            double dayPnl = DayPnl();
            if (dayPnl >= DailyProfitCap || dayPnl <= -DailyLossStop)
                doneForDay = true;
            if (ProfitSoFar + dayPnl >= ProfitTarget)
                doneForDay = true; // target reached - stop and let the day close

            if (doneForDay || !orReady || t <= OrEnd || t > LastEntryTime)
                return;
            if (Position.MarketPosition != MarketPosition.Flat || tradesToday >= MaxTradesPerDay)
                return;

            // 4) breakout signal on a closed 1-min bar
            bool longSignal = !tradedLong && Close[0] > orHigh && Close[1] <= orHigh;
            bool shortSignal = !tradedShort && Close[0] < orLow && Close[1] >= orLow;
            if (!longSignal && !shortSignal)
                return;

            double range = orHigh - orLow;
            double stopPts = Math.Max(MinStopPoints, Math.Min(MaxStopPoints, range));
            double pointValue = Instrument.MasterInstrument.PointValue;

            // never risk more than the room left above the drawdown floor
            // and never more than what is left of today's loss allowance
            double risk = Math.Min(RiskDollars, DailyLossStop + Math.Min(0, dayPnl));
            double room = RoomToFloor();
            if (room > 0)
                risk = Math.Min(risk, room - FloorBuffer);

            int qty = (int)Math.Floor(risk / (stopPts * pointValue));
            qty = Math.Min(qty, MaxContracts);
            if (qty < 1)
            {
                doneForDay = true;
                return;
            }

            // consistency: a full win today must not push the day above DailyProfitCap by much
            double targetPts = stopPts * RewardRisk;
            double winDollars = qty * targetPts * pointValue;
            double maxWin = DailyProfitCap * 1.10 - Math.Max(0, dayPnl);
            if (winDollars > maxWin && maxWin > 0)
                targetPts = Math.Max(TickSize * 4, maxWin / (qty * pointValue));

            int stopTicks = (int)Math.Round(stopPts / TickSize);
            int targetTicks = (int)Math.Round(targetPts / TickSize);

            if (longSignal)
            {
                SetStopLoss("ORB_L", CalculationMode.Ticks, stopTicks, false);
                SetProfitTarget("ORB_L", CalculationMode.Ticks, targetTicks);
                EnterLong(qty, "ORB_L");
                tradedLong = true;
            }
            else
            {
                SetStopLoss("ORB_S", CalculationMode.Ticks, stopTicks, false);
                SetProfitTarget("ORB_S", CalculationMode.Ticks, targetTicks);
                EnterShort(qty, "ORB_S");
                tradedShort = true;
            }
            tradesToday++;
        }

        private void ResetDay()
        {
            orReady = false;
            orHigh = 0;
            orLow = 0;
            tradesToday = 0;
            doneForDay = false;
            tradedLong = false;
            tradedShort = false;
            dayStartCumProfit = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
        }

        private double DayPnl()
        {
            double realized = SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit - dayStartCumProfit;
            double open = Position.MarketPosition == MarketPosition.Flat
                ? 0
                : Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
            return realized + open;
        }

        private double RoomToFloor()
        {
            if (!UseAccountBalance || State != State.Realtime || Account == null)
                return -1; // unknown in backtests - rely on RiskDollars
            double cash = Account.Get(AccountItem.CashValue, Currency.UsDollar);
            return cash - DrawdownFloor;
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "Mode (Sprint / Steady)", Order = 0, GroupName = "1. Plan")]
        public LucidBotMode Mode { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Opening range start (HHmmss ET)", Order = 1, GroupName = "2. Session")]
        public int OrStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Opening range end (HHmmss ET)", Order = 2, GroupName = "2. Session")]
        public int OrEnd { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Last entry time (HHmmss ET)", Order = 3, GroupName = "2. Session")]
        public int LastEntryTime { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Flatten time (HHmmss ET)", Order = 4, GroupName = "2. Session")]
        public int FlattenTime { get; set; }

        [NinjaScriptProperty]
        [Range(1, 500)]
        [Display(Name = "Min stop (points)", Order = 1, GroupName = "3. Trade")]
        public double MinStopPoints { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name = "Max stop (points)", Order = 2, GroupName = "3. Trade")]
        public double MaxStopPoints { get; set; }

        [NinjaScriptProperty]
        [Range(10, 5000)]
        [Display(Name = "Risk per trade ($)", Order = 3, GroupName = "3. Trade")]
        public double RiskDollars { get; set; }

        [NinjaScriptProperty]
        [Range(0.2, 10)]
        [Display(Name = "Reward : Risk", Order = 4, GroupName = "3. Trade")]
        public double RewardRisk { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max trades per day", Order = 5, GroupName = "3. Trade")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(1, 400)]
        [Display(Name = "Max contracts", Order = 6, GroupName = "3. Trade")]
        public int MaxContracts { get; set; }

        [NinjaScriptProperty]
        [Range(10, 10000)]
        [Display(Name = "Daily profit cap ($) - consistency", Order = 1, GroupName = "4. Lucid rules")]
        public double DailyProfitCap { get; set; }

        [NinjaScriptProperty]
        [Range(10, 10000)]
        [Display(Name = "Daily loss stop ($)", Order = 2, GroupName = "4. Lucid rules")]
        public double DailyLossStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Evaluation profit target ($)", Order = 3, GroupName = "4. Lucid rules")]
        public double ProfitTarget { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Profit so far on account ($) - update daily", Order = 4, GroupName = "4. Lucid rules")]
        public double ProfitSoFar { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Drawdown floor ($) - copy from Lucid dashboard", Order = 5, GroupName = "4. Lucid rules")]
        public double DrawdownFloor { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Buffer above floor ($)", Order = 6, GroupName = "4. Lucid rules")]
        public double FloorBuffer { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Read live account balance", Order = 7, GroupName = "4. Lucid rules")]
        public bool UseAccountBalance { get; set; }
        #endregion
    }
}
