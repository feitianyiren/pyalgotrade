# PyAlgoTrade
# 
# Copyright 2012 Gabriel Martin Becedillas Ruiz
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

from pyalgotrade import stratanalyzer
from pyalgotrade import broker
from pyalgotrade.stratanalyzer import returns

import numpy as np

class Trades(stratanalyzer.StrategyAnalyzer):
	"""A :class:`pyalgotrade.stratanalyzer.StrategyAnalyzer` that records the profit/loss
	and returns of every completed trade.

	.. note::
		This analyzer operates on individual completed trades.
		For example, lets say you start with a $1000 cash, and then you buy 1 share of XYZ
		for $10 and later sell it for $20:

			* The trade's profit was $10.
			* The trade's return is 100%, even though your whole portfolio went from $1000 to $1020, a 2% return.
	"""

	def __init__(self):
		self.__all = []
		self.__profits = []
		self.__losses = []
		self.__allReturns = []
		self.__positiveReturns = []
		self.__negativeReturns = []
		self.__evenTrades = 0
		self.__posTrackers = {}

	def __updateTrades(self, posTracker):
		price = 0 # The price doesn't matter since the position should be closed.
		assert(posTracker.getShares() == 0)
		netProfit =  posTracker.getNetProfit(price)
		netReturn =  posTracker.getReturn(price)

		if netProfit > 0:
			self.__profits.append(netProfit)
			self.__positiveReturns.append(netReturn )
		elif netProfit < 0:
			self.__losses.append(netProfit)
			self.__negativeReturns.append(netReturn )
		else:
			self.__evenTrades += 1

		self.__all.append(netProfit)
		self.__allReturns.append(netReturn)

		posTracker.update(price)

	def __updatePosTracker(self, posTracker, price, commission, quantity):
		currentShares = posTracker.getShares()

		if currentShares > 0: # Current position is long
			if quantity > 0: # Increase long position
				posTracker.buy(quantity, price, commission)
			else:
				newShares = currentShares + quantity
				if newShares == 0: # Exit long.
					posTracker.sell(currentShares, price, commission)
					self.__updateTrades(posTracker)
				elif newShares > 0: # Sell some shares.
					posTracker.sell(quantity*-1, price, commission)
				else: # Exit long and enter short. Use proportional commissions.
					posTracker.sell(currentShares, price, commission / float(currentShares))
					self.__updateTrades(posTracker)
					posTracker.sell(newShares*-1, price, commission / float(newShares*-1))
		elif currentShares < 0: # Current position is short
			if quantity < 0: # Increase short position
				posTracker.sell(quantity*-1, price, commission)
			else:
				newShares = currentShares + quantity
				if newShares == 0: # Exit short.
					posTracker.buy(currentShares*-1, price, commission)
					self.__updateTrades(posTracker)
				elif newShares < 0: # Re-buy some shares.
					posTracker.buy(quantity, price, commission)
				else: # Exit short and enter long. Use proportional commissions.
					posTracker.buy(currentShares*-1, price, commission / float(currentShares*-1))
					self.__updateTrades(posTracker)
					posTracker.buy(newShares, price, commission / float(newShares))
		elif quantity > 0:
			posTracker.buy(quantity, price, commission)
		else:
			posTracker.sell(quantity*-1, price, commission)

	def __onOrderUpdate(self, broker_, order):
		# Only interested in filled orders.
		if not order.isFilled():
			return

		# Get or create the tracker for this instrument.
		try:
			posTracker = self.__posTrackers[order.getInstrument()]
		except KeyError:
			posTracker = returns.PositionTracker()
			self.__posTrackers[order.getInstrument()] = posTracker

		# Update the tracker for this order.
		price = order.getExecutionInfo().getPrice()
		commission = order.getExecutionInfo().getCommission()
		action = order.getAction()
		if action in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
			quantity = order.getExecutionInfo().getQuantity()
		elif action in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
			quantity = order.getExecutionInfo().getQuantity() * -1
		else: # Unknown action
			assert(False)

		self.__updatePosTracker(posTracker, price, commission, quantity)

	def attached(self, strat):
		strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderUpdate)

	def getCount(self):
		"""Returns the total number of trades."""
		return len(self.__all)

	def getProfitableCount(self):
		"""Returns the number of profitable trades."""
		return len(self.__profits)

	def getUnprofitableCount(self):
		"""Returns the number of unprofitable trades."""
		return len(self.__losses)

	def getEvenCount(self):
		"""Returns the number of trades whose net profit was 0."""
		return self.__evenTrades

	def getAll(self):
		"""Returns a numpy.array with the profits/losses for each trade."""
		return np.array(self.__all)

	def getProfits(self):
		"""Returns a numpy.array with the profits for each profitable trade."""
		return np.array(self.__profits)

	def getLosses(self):
		"""Returns a numpy.array with the losses for each unprofitable trade."""
		return np.array(self.__losses)

	def getAllReturns(self):
		"""Returns a numpy.array with the returns for each trade."""
		return np.array(self.__allReturns)

	def getPositiveReturns(self):
		"""Returns a numpy.array with the positive returns for each trade."""
		return np.array(self.__positiveReturns)

	def getNegativeReturns(self):
		"""Returns a numpy.array with the negative returns for each trade."""
		return np.array(self.__negativeReturns)

